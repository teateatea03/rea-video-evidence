"""Timestamped subtitles and optional, explicitly local faster-whisper ASR."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from .integrity import digest, atomic_json

SCHEMA = "rea-video.transcript.v1"


def timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) not in (2, 3):
        raise ValueError("subtitle timestamp needs MM:SS or HH:MM:SS")
    nums = [float(v) for v in parts]
    if any(not math.isfinite(v) or v < 0 for v in nums) or nums[-1] >= 60 or (len(nums) == 3 and nums[-2] >= 60):
        raise ValueError("invalid subtitle timestamp")
    return sum(v * 60 ** i for i, v in enumerate(reversed(nums)))


def validate_segments(segments, duration: float):
    if not isinstance(segments, list) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid transcript duration/segments")
    result = []
    for i, s in enumerate(segments):
        if not isinstance(s, dict) or isinstance(s.get("start"), bool) or isinstance(s.get("end"), bool):
            raise ValueError("transcript segment must have numeric bounds")
        start, end = float(s["start"]), float(s["end"])
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration + 0.05:
            raise ValueError(f"transcript segment {i + 1} outside source duration")
        if not isinstance(s.get("text"), str) or not s["text"].strip():
            raise ValueError("transcript text must be non-empty")
        sid = s.get("id", f"speech_{i + 1:05d}")
        if not isinstance(sid, str) or not sid:
            raise ValueError("invalid transcript segment id")
        result.append({"id": sid, "start": start, "end": end, "text": s["text"].strip()})
    if len({s["id"] for s in result}) != len(result):
        raise ValueError("transcript segment ids must be unique")
    return sorted(result, key=lambda s: (s["start"], s["end"], s["id"]))


def parse_subtitles(path: str | Path, duration: float):
    path = Path(path)
    if path.suffix.lower() not in (".srt", ".vtt"):
        raise ValueError("only SRT/VTT subtitles are supported")
    if path.stat().st_size > 32 << 20:
        raise ValueError("subtitle file exceeds 32 MiB")
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    segments = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            # WebVTT header and metadata blocks; reject malformed cue blocks.
            if block.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
                continue
            raise ValueError("subtitle cue is missing its timestamp")
        left, right = lines[timing].split("-->", 1)
        body = "\n".join(lines[timing + 1:]).strip()
        segments.append({"start": timestamp(left.strip()), "end": timestamp(right.strip().split()[0]), "text": body})
    return validate_segments(segments, duration)


def import_transcript(report: str | Path, subtitles: str | Path, *, origin="supplied_subtitles", language="unknown"):
    root = Path(report).resolve()
    b = json.loads((root / "breakdown.json").read_text(encoding="utf-8"))
    sha = b["source"].get("sha256")
    if not sha:
        raise ValueError("transcript binding requires a full source SHA-256; re-analyze this legacy report")
    if origin not in ("manual_subtitles", "automatic_subtitles", "supplied_subtitles"):
        raise ValueError("invalid subtitle origin")
    result = {"schema": SCHEMA, "source_sha256": sha, "duration": b["source"]["duration"],
              "origin": origin, "language": language, "subtitle_sha256": digest(subtitles),
              "segments": parse_subtitles(subtitles, float(b["source"]["duration"])),
              "verification": "unverified_text_not_listening"}
    target = root / "transcript.json"
    if target.exists():
        raise ValueError("transcript.json already exists; preserve it and use a new report directory")
    atomic_json(target, result)
    return result


def load_transcript(path: Path, source: dict):
    if not path.is_file():
        return {"status": "not_recorded", "segments": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not source.get("sha256") or data.get("source_sha256") != source["sha256"]:
        raise ValueError("transcript source binding does not match")
    data["segments"] = validate_segments(data.get("segments"), float(source["duration"]))
    return {**data, "status": "available"}


def transcribe_local(video: str | Path, output: str | Path, model: str | Path, language=None):
    """No model identifiers or remote downloads: require a local CTranslate2 model folder."""
    from .media import video_info
    model = Path(model).expanduser().resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("ASR output already exists")
    required = ("model.bin", "config.json", "tokenizer.json")
    if not model.is_dir() or not all((model / name).is_file() for name in required):
        raise ValueError("--model must be a complete local faster-whisper directory: model.bin, config.json, tokenizer.json")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"schema": SCHEMA, "status": "unavailable", "reason": "install the optional asr extra in the dedicated environment"}
    info = video_info(video)
    if not info.has_audio:
        return {"schema": SCHEMA, "status": "unavailable", "reason": "no_audio"}
    source_sha = digest(video)
    engine = WhisperModel(str(model), device="cpu", compute_type="int8", local_files_only=True)
    segments, metadata = engine.transcribe(str(video), language=language, vad_filter=True)
    rows = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
    if digest(video) != source_sha:
        raise ValueError("source changed during transcription")
    import importlib.metadata
    try:
        runtime_version = importlib.metadata.version("faster-whisper")
    except importlib.metadata.PackageNotFoundError:
        runtime_version = "unknown"
    result = {"schema": SCHEMA, "status": "available", "origin": "asr", "runtime_version": runtime_version,
              "source_sha256": source_sha, "duration": info.duration,
              "language": metadata.language, "model": model.name, "model_sha256": digest(model / "model.bin"),
              "segments": validate_segments(rows, info.duration), "verification": "unverified_text_not_listening"}
    atomic_json(output, result)
    return result
