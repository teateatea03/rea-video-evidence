"""Failure and timestamp cases beyond the normal evidence workflow."""
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest

from rea_video import inspection, media
from rea_video.ocr_budget import OCRBudget
from rea_video.transcript import validate_segments
from rea_video.integrity import digest, atomic_json


def test_segment_ids_survive_sort_and_reload():
    rows = [{"start": 2, "end": 3, "text": "late"}, {"start": 0, "end": 1, "text": "early"}]
    normalized = validate_segments(rows, 4)
    assert validate_segments(normalized, 4) == normalized
    with pytest.raises(ValueError, match="unique"):
        validate_segments([normalized[0], normalized[0]], 4)


def test_timestamp_fallback_is_distinguished_from_cfr(monkeypatch):
    details = {}
    monkeypatch.setattr(media.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="0\n0.033333\n"))
    assert media.frame_times("fake", 3, 30, details) is None
    assert details["status"] == "estimated" and "mismatch" in details["reason"]
    assert media.frame_times("fake", 2, 30, details) is None
    assert details["status"] == "packet_aligned_cfr"
    monkeypatch.setattr(media.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="0\n0.2\n0.7\n"))
    times = media.frame_times("fake", 3, 30, details)
    assert times.tolist() == [0, .2, .7] and details["method"] == "packet_pts"


def test_nonzero_stream_start_uses_relative_pts(media, tmp_path):
    shifted = tmp_path / "shifted.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(media["code"]), "-c", "copy",
                    "-output_ts_offset", "5", str(shifted)], check=True)
    result = inspection.sample_window(shifted, tmp_path / "frames", start=.5, end=2, max_frames=2, width=160)
    assert result["status"] == "ok", result
    assert abs(result["frames"][0]["time"] - .5) < .06


def test_failed_samples_are_reported_without_claimed_success(media, tmp_path, monkeypatch):
    monkeypatch.setattr(inspection, "extract", lambda *a, **kw: (_ for _ in ()).throw(media_error()))
    result = inspection.sample_window(media["code"], tmp_path / "frames", max_frames=2, width=160)
    assert result["status"] == "failed" and result["returned"] == 0 and len(result["failures"]) == 2


def media_error():
    return inspection.MediaError("synthetic extraction failure")


def test_spoken_claim_requires_real_segment_and_inferred_requires_uncertainty(tmp_path):
    image = tmp_path / "f.jpg"
    image.write_bytes(b"image")
    manifest = {"source_sha256": "source", "duration": 5, "frames": [
        {"id": "f1", "time": 1, "path": "f.jpg", "sha256": digest(image)}]}
    atomic_json(tmp_path / "manifest.json", manifest)
    claim = {"text": "something", "start": 0, "end": 2, "kind": "spoken", "support": "supported", "segments": ["absent"]}
    with pytest.raises(ValueError, match="spoken"):
        inspection.validate_claims({"source_sha256": "source", "claims": [claim]}, tmp_path / "manifest.json")
    claim.update(kind="inferred", frames=["f1"], segments=[])
    with pytest.raises(ValueError, match="uncertainty"):
        inspection.validate_claims({"source_sha256": "source", "claims": [claim]}, tmp_path / "manifest.json")


@pytest.mark.parametrize("limit", [-1, True, 1.2])
def test_invalid_ocr_budget_is_rejected(limit):
    with pytest.raises(ValueError):
        OCRBudget(limit)
