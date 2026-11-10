"""Source safety, OCR budgets and transcript/inspection integration regressions."""
from copy import deepcopy
import json
import math
import sys
from types import SimpleNamespace
from pathlib import Path

import numpy as np
import pytest

from rea_video.integrity import binding, digest, atomic_json
from rea_video.review import apply_answers, _clean
from rea_video.ocr_budget import OCRBudget
from rea_video import packaging, overlay, inspection
from rea_video.transcript import import_transcript, parse_subtitles, transcribe_local
from rea_video.evidence import evidence_pack, IntervalIndex
from rea_video.cli import main


def report(tmp_path):
    video = tmp_path / "source.mp4"
    video.write_bytes(b"synthetic source identity, not decoded")
    image = tmp_path / "sheet.jpg"
    image.write_bytes(b"synthetic image")
    b = {"source": {"path": str(video), "filename": video.name, "sha256": digest(video), "duration": 6},
         "shots": [{"id": "shot_001", "start": 0, "end": 6, "base": {"label": "ai_video", "confidence": .5},
                    "deterministic": {"probs": {"ai_video": .5, "live_action": .5}, "facts": {}, "evidence": []},
                    "assets": {"sheet": "sheet.jpg"}}]}
    atomic_json(tmp_path / "breakdown.json", b)
    answer = {"binding": binding(b, tmp_path), "shots": [{"id": "shot_001", "time": "0.00-6.00",
              "label_probs": {"ai_video": 1}, "evidence": ["inspected synthetic sheet"]}]}
    return b, answer


@pytest.mark.parametrize("value", ["inf", "-inf", "nan", True, -0.5, None, [], {}])
def test_nonfinite_and_invalid_probabilities_are_rejected(value):
    clean, error = _clean({"label_probs": {"ai_video": value}})
    assert clean is None and error


def test_source_binding_rejects_wrong_source_without_mutation(tmp_path):
    b, answer = report(tmp_path)
    before = deepcopy(b)
    answer["binding"]["source_sha256"] = "another source"
    with pytest.raises(ValueError, match="source"):
        apply_answers(b, answer, report_dir=tmp_path)
    assert b == before


def test_binding_survives_partial_review_but_rejects_changed_images_and_source(tmp_path):
    b, answer = report(tmp_path)
    assert apply_answers(b, answer, report_dir=tmp_path)["applied"] == ["shot_001"]
    assert apply_answers(b, answer, report_dir=tmp_path)["applied"] == ["shot_001"]
    (tmp_path / "sheet.jpg").write_bytes(b"changed")
    with pytest.raises(ValueError, match="images"):
        apply_answers(b, answer, report_dir=tmp_path)
    answer["binding"] = binding(b, tmp_path)
    Path(b["source"]["path"]).write_bytes(b"modified source")
    with pytest.raises(ValueError, match="source video changed"):
        apply_answers(b, answer, report_dir=tmp_path)


def test_legacy_is_explicit_and_wrong_time_or_empty_evidence_does_not_apply(tmp_path):
    b, answer = report(tmp_path)
    legacy = deepcopy(answer)
    del legacy["binding"]
    with pytest.raises(ValueError, match="legacy"):
        apply_answers(b, legacy)
    assert apply_answers(b, legacy, allow_legacy=True)["binding_status"] == "legacy_unbound"
    answer["shots"][0]["time"] = "1.00-2.00"
    assert apply_answers(b, answer)["applied"] == []
    answer["shots"][0]["time"] = "0.00-6.00"
    answer["shots"][0]["evidence"] = []
    assert apply_answers(b, answer)["applied"] == []


def test_duplicate_review_ids_are_rejected_before_changes(tmp_path):
    b, answer = report(tmp_path)
    answer["shots"] *= 2
    with pytest.raises(ValueError, match="unique"):
        apply_answers(b, answer)
    assert "review" not in b["shots"][0]


def test_malformed_probability_container_is_reported(tmp_path):
    b, answer = report(tmp_path)
    answer["shots"][0]["label_probs"] = ["ai_video"]
    assert apply_answers(b, answer)["problems"]


def test_ocr_budget_is_shared_with_fallback_and_errors_are_distinct(monkeypatch):
    calls = []
    def ocr(frame):
        calls.append(1)
        return [], None
    def frames(path, info, width, **kw):
        for i in range(math.ceil(info.duration * kw["fps"])):
            yield np.full((16, 16, 3), 255 * (i % 2), np.uint8)
    monkeypatch.setattr(packaging, "get_ocr", lambda: ocr)
    monkeypatch.setattr(packaging, "iter_frames", frames)
    monkeypatch.setattr(overlay, "get_ocr", lambda: ocr)
    budget = OCRBudget(240)
    info = SimpleNamespace(duration=600, width=16, height=16, rotation=0)
    _, step = packaging.ocr_pass("fake", info, budget=budget)
    overlay.ocr_frames([np.zeros((16, 16, 3), np.uint8)], [0], budget=budget)
    assert len(calls) == budget.used == 240 and step == 2.5
    assert budget.summary()["status"] == "partial"
    monkeypatch.setattr(packaging, "get_ocr", lambda: None)
    missing = OCRBudget(5)
    packaging.ocr_pass("fake", info, budget=missing)
    assert missing.summary()["status"] == "unavailable"
    assert missing.summary(enabled=False)["status"] == "off"


def test_ocr_cache_reuse_is_counted_without_extra_calls(monkeypatch):
    def frames(*a, **kw):
        for _ in range(10):
            yield np.zeros((16, 16, 3), np.uint8)
    monkeypatch.setattr(packaging, "iter_frames", frames)
    monkeypatch.setattr(packaging, "get_ocr", lambda: lambda f: ([], None))
    budget = OCRBudget(4)
    packaging.ocr_pass("fake", SimpleNamespace(duration=20, width=16, height=16, rotation=0), budget=budget)
    assert budget.used == 1 and budget.reused == 9


@pytest.mark.parametrize("extension", ["srt", "vtt"])
def test_subtitles_are_bound_searchable_and_distinct_from_ocr(tmp_path, extension):
    b, _ = report(tmp_path)
    text = ("1\n00:00:01,000 --> 00:00:02,000\n你好 hello 日本語 한국어\n" if extension == "srt" else
            "WEBVTT\n\n00:01.000 --> 00:02.000 align:start\n你好 hello 日本語 한국어\n")
    sub = tmp_path / f"text.{extension}"
    sub.write_text(text, encoding="utf-8")
    import_transcript(tmp_path, sub, language="multilingual")
    before = {p.name: digest(p) for p in tmp_path.iterdir() if p.is_file()}
    result = evidence_pack(tmp_path, query="한국어", start=1, end=2)
    assert result["shots"][0]["query_matches"][0]["origin"] == "spoken"
    assert result["shots"][0]["screen_text"]["total"] == 0
    assert result["shots"][0]["spoken"]["items"][0]["text"].startswith("你好")
    assert evidence_pack(tmp_path, query="한국어", start=2, end=3)["shots"] == []
    assert {p.name: digest(p) for p in tmp_path.iterdir() if p.is_file()} == before
    b["source"]["sha256"] = "wrong"
    atomic_json(tmp_path / "breakdown.json", b)
    with pytest.raises(ValueError, match="binding"):
        evidence_pack(tmp_path)


def test_invalid_subtitle_timing_is_rejected(tmp_path):
    p = tmp_path / "x.srt"
    p.write_text("1\n00:00:01,000 --> 00:00:09,000\noutside\n", encoding="utf-8")
    with pytest.raises(ValueError, match="outside"):
        parse_subtitles(p, 6)


def test_interval_index_matches_bruteforce_for_overlapping_rows():
    rows = [{"t0": i / 2, "t1": i / 2 + (10 if i % 3 == 0 else .2)} for i in range(100)]
    index = IntervalIndex(rows)
    for t in np.arange(0, 50, .3):
        assert index.overlap(t, t + .5) == [r for r in rows if r["t0"] < t + .5 and r["t1"] > t]


def test_inspect_uses_decoded_source_relative_pts(media, tmp_path):
    m = inspection.sample_window(media["code"], tmp_path / "inspect", start=.5, end=2.5, max_frames=3, width=320)
    assert m["status"] == "ok", m
    assert all(.5 <= f["time"] < 2.5 for f in m["frames"])
    assert abs(m["frames"][0]["time"] - .5) < .05
    claims = {"source_sha256": m["source_sha256"], "claims": [
        {"text": "Synthetic observation", "start": .5, "end": 2.5, "kind": "observed", "support": "supported", "frames": [m["frames"][0]["id"]]}]}
    manifest = tmp_path / "inspect" / "manifest.json"
    assert inspection.validate_claims(claims, manifest)["status"] == "valid"
    (manifest.parent / m["frames"][0]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="integrity"):
        inspection.validate_claims(claims, manifest)


def test_chapters_resume_verifies_and_reuses_frames(media, tmp_path, monkeypatch):
    out = tmp_path / "chapters"
    first = inspection.chapter_index(media["code"], out, chunk_seconds=1, overlap=.1, max_frames=1, width=160)
    monkeypatch.setattr(inspection, "sample_window", lambda *a, **kw: pytest.fail("completed chapters must not decode"))
    again = inspection.chapter_index(media["code"], out, chunk_seconds=1, overlap=.1, max_frames=1, width=160, resume=True)
    assert again == first
    with pytest.raises(ValueError, match="settings"):
        inspection.chapter_index(media["code"], out, chunk_seconds=2, overlap=.1, max_frames=1, width=160, resume=True)
    c = first["chapters"][0]
    (out / c["manifest"]).write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        inspection.chapter_index(media["code"], out, chunk_seconds=1, overlap=.1, max_frames=1, width=160, resume=True)


def test_chapters_resume_after_interruption_preserves_global_time(media, tmp_path, monkeypatch):
    real = inspection.sample_window
    calls = []
    def interrupt(*a, **kw):
        calls.append(kw["start"])
        if len(calls) == 2:
            raise RuntimeError("synthetic interruption")
        return real(*a, **kw)
    monkeypatch.setattr(inspection, "sample_window", interrupt)
    out = tmp_path / "chapters"
    with pytest.raises(RuntimeError):
        inspection.chapter_index(media["code"], out, chunk_seconds=1, overlap=0, max_frames=1, width=160)
    assert len(json.loads((out / "chapters.json").read_text())["chapters"]) == 1
    monkeypatch.setattr(inspection, "sample_window", real)
    final = inspection.chapter_index(media["code"], out, chunk_seconds=1, overlap=0, max_frames=1, width=160, resume=True)
    second = json.loads((out / final["chapters"][1]["manifest"]).read_text())
    assert second["frames"][0]["time"] >= 1


def test_local_asr_adapter_does_not_accept_remote_model_or_download(tmp_path, monkeypatch):
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"fake model")
    (model / "config.json").write_text("{}", encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    video = tmp_path / "video"
    video.write_bytes(b"fake audio video")
    from rea_video import media as media_module
    monkeypatch.setattr(media_module, "video_info", lambda p: SimpleNamespace(duration=3, has_audio=True))
    class Model:
        def __init__(self, path, **kw):
            assert Path(path) == model and kw["local_files_only"] is True
        def transcribe(self, *a, **kw):
            return iter([SimpleNamespace(start=0, end=1, text="hello")]), SimpleNamespace(language="en")
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    result = transcribe_local(video, tmp_path / "transcript.json", model)
    assert result["origin"] == "asr" and result["segments"][0]["text"] == "hello"
    with pytest.raises(ValueError, match="local"):
        transcribe_local(video, tmp_path / "other.json", "not-a-remote-model")


def test_read_only_commands_do_not_load_env(monkeypatch, capsys):
    from rea_video import cli, doctor
    monkeypatch.setattr(cli, "_env", lambda a: pytest.fail("must not load credentials/prefs"))
    monkeypatch.setattr(doctor, "diagnose", lambda: {"status": "ready"})
    assert main(["doctor", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ready"
    assert main(["inspect", "missing", "-o", "ignored", "--max-frames", "0"]) == 2
