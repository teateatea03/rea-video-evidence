"""Evidence retrieval must preserve time, origin, coverage and resource bounds."""
import hashlib
import json

import pytest

from rea_video.cli import main
from rea_video.evidence import evidence_pack


@pytest.fixture
def report(tmp_path):
    folder = tmp_path / "中文 報告"
    (folder / "shots").mkdir(parents=True)
    (folder / "shots" / "s1.jpg").write_bytes(b"existence check only")
    shots = []
    for i in range(3):
        shots.append({
            "id": f"s{i + 1}", "start": i * 2, "end": (i + 1) * 2,
            "deterministic": {"probs": {"code_render": 0.95, "ai_video": 0.05} if i == 0
                              else {"ai_video": 0.52, "live_action": 0.48}, "facts": {},
                              "evidence": ["measured cadence"]},
            "base": {"label": "code_render" if i == 0 else "ai_video", "confidence": 0.95 if i == 0 else 0.52},
            "assets": {"sheet": f"shots/s{i + 1}.jpg"},
        })
    shots[1]["review"] = {"label_probs": {"ai_video": 0.6, "live_action": 0.4},
                          "_by": "reviewer", "description": "藍色產品", "evidence": ["saw a blue object"]}
    data = {
        "source": {"duration": 6, "path": "source.mp4", "filename": "source.mp4"},
        "shots": shots, "analysis": {"vlm": {"status": "off"}, "review": {"shots": 99}},
        "audio": {"has_audio": False},
        "packaging": {"text_cues": [
            {"id": "ocr1", "t0": 0, "t1": 2, "text": "第一頁", "kind": "title"},
            {"id": "ocr2", "t0": 2, "t1": 4, "text": "中文搜尋 SFX [a-z]", "kind": "subtitle"},
        ]},
    }
    path = folder / "breakdown.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path, data


def save(report):
    path, data = report
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_time_windows_are_half_open_and_do_not_bleed_ocr(report):
    path, _ = report
    pack = evidence_pack(path.parent, start=2, end=4)
    assert [r["id"] for r in pack["shots"]] == ["s2"]
    assert pack["shots"][0]["citation"] == "s2@2.000-4.000s"
    assert [r["id"] for r in pack["shots"][0]["screen_text"]["items"]] == ["ocr2"]
    assert evidence_pack(path, start=1.9, end=2.1)["coverage"]["window_shots"] == 2


def test_keywords_match_ocr_and_applied_review_as_literal_text(report):
    path, _ = report
    for query in ("中文搜尋", "sfx", "[a-z]", "藍色產品"):
        pack = evidence_pack(path, query=query)
        assert [r["id"] for r in pack["shots"]] == ["s2"]
        assert pack["shots"][0]["query_matches"]
    assert evidence_pack(path, query="not present")["shots"] == []


def test_pending_queue_uses_actual_records_and_prioritizes_uncertainty(report):
    path, _ = report
    pack = evidence_pack(path, pending=True)
    assert [r["id"] for r in pack["shots"]] == ["s3", "s1"]
    assert pack["coverage"] == {"window_shots": 3, "applied_review_shots": 1, "unreviewed_high_priority": 1}
    assert pack["vlm_status"] == "off"  # a review never pretends the external VLM ran
    assert pack["audio"]["listening_verification"] == "not_recorded"


def test_missing_and_outside_assets_are_not_claimed_available(report, tmp_path):
    path, data = report
    data["shots"][1]["assets"]["sheet"] = "../private.jpg"
    data["shots"][2]["assets"]["sheet"] = "C:/private.jpg"
    pack = evidence_pack(save(report))
    statuses = [r["images"]["sheet"]["status"] for r in pack["shots"]]
    assert statuses == ["available", "outside_report", "outside_report"]
    assert pack["shots"][0]["images"]["first_frame"]["status"] == "not_recorded"
    assert pack["shots"][1]["images"]["sheet"]["path"] is None
    data["shots"][1]["assets"]["sheet"] = "shots/missing.jpg"
    assert evidence_pack(save(report))["shots"][1]["images"]["sheet"]["status"] == "missing"


def test_output_is_bounded_and_paginates_without_changing_report(report):
    path, data = report
    data["shots"][0]["review"] = {"label_probs": {"code_render": 1}, "description": "A" * 9000}
    data["packaging"]["text_cues"] += [{"id": f"extra{i}", "t0": 0, "t1": 2, "text": "x" * 5000} for i in range(30)]
    save(report)
    before = path.read_bytes()
    first = evidence_pack(path, limit=1)
    assert first["pagination"]["matched"] == 3 and first["pagination"]["next_offset"] == 1
    assert first["pagination"]["truncated"]
    shot = first["shots"][0]
    assert len(shot["agent_review"]["description"]) <= 241
    assert len(shot["screen_text"]["items"]) == 8 and shot["screen_text"]["truncated"]
    second = evidence_pack(path, limit=2, offset=1)
    assert [r["id"] for r in second["shots"]] == ["s2", "s3"]
    assert second["pagination"]["next_offset"] is None
    assert path.read_bytes() == before
    assert first["breakdown_sha256"] == hashlib.sha256(before).hexdigest()


@pytest.mark.parametrize("options", [
    {"start": -1}, {"start": float("nan")}, {"start": float("inf")},
    {"end": float("nan")}, {"end": 0}, {"start": 4, "end": 2}, {"end": 7},
    {"limit": 0}, {"limit": 101}, {"limit": True}, {"offset": -1}, {"query": "a" * 201},
])
def test_invalid_scope_and_budgets_fail_explicitly(report, options):
    with pytest.raises(ValueError):
        evidence_pack(report[0], **options)


def test_cli_json_does_not_load_credentials_or_write_artifacts(report, monkeypatch, capsys):
    def forbidden(*args):
        raise AssertionError("evidence command must not load .env or prefs")
    monkeypatch.setattr("rea_video.cli._env", forbidden)
    path = report[0]
    before = {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()}
    assert main(["evidence", str(path), "--start", "2", "--end", "4", "--limit", "1"]) == 0
    captured = capsys.readouterr()
    pack = json.loads(captured.out)
    assert pack["shots"][0]["id"] == "s2" and not captured.err
    assert {p.name: p.read_bytes() for p in path.parent.iterdir() if p.is_file()} == before


def test_ambiguous_shot_citations_are_rejected(report):
    _, data = report
    data["shots"][2]["id"] = "s1"
    with pytest.raises(ValueError, match="unique"):
        evidence_pack(save(report))


def test_keyword_match_keeps_evidence_origin_even_beyond_excerpt_budget(report):
    _, data = report
    data["shots"][0]["deterministic"]["evidence"] = ["unrelated"] * 8 + ["needle measurement"]
    path = save(report)
    match = evidence_pack(path, query="needle")["shots"][0]["query_matches"][0]
    assert match == {"origin": "measurement", "text": "needle measurement"}
    match = evidence_pack(path, query="中文搜尋")["shots"][0]["query_matches"][0]
    assert match["origin"] == "screen_text"
    match = evidence_pack(path, query="藍色產品")["shots"][0]["query_matches"][0]
    assert match["origin"] == "agent_review"


def test_cli_invalid_options_and_bad_reports_do_not_traceback(report, capsys):
    assert main(["evidence", str(report[0]), "--limit", "0"]) == 2
    assert "Traceback" not in capsys.readouterr().err
    report[0].write_text("{}", encoding="utf-8")
    assert main(["evidence", str(report[0])]) == 2
    assert "expected a rea-video breakdown" in capsys.readouterr().err
