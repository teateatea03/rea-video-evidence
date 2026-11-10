"""Bounded focused sampling, original-PTS evidence and resumable chapter indexes."""
from __future__ import annotations
import json
import math
import re
import subprocess
import uuid
from pathlib import Path
from .integrity import digest, atomic_json, identity
from .media import video_info, scaled_size, passthrough_args, MediaError
from . import __version__


def finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be finite") from None
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def window(duration, start, end):
    start = finite(start, "start")
    end = duration if end is None else finite(end, "end")
    if not 0 <= start < end <= duration:
        raise ValueError("require 0 <= start < end <= source duration")
    return start, end


def extract(video, info, t, path, width, crop=None):
    w, h = scaled_size(info, width)
    filters = ["showinfo"]
    if crop:
        x, y, cw, ch = crop
        filters += [f"crop=iw*{cw}:ih*{ch}:iw*{x}:ih*{y}", f"scale={width}:-2"]
    else:
        filters += [f"scale={w}:{h}"]
    # copyts/start_at_zero retain decoded PTS on the source-relative timeline after seeking.
    command = ["ffmpeg", "-v", "info", "-nostdin", "-ss", f"{t:.6f}", "-copyts", "-start_at_zero",
               "-i", str(video), "-map", "0:V:0", "-frames:v", "1", "-an", "-sn",
               "-vf", ",".join(filters), *passthrough_args(), str(path)]
    p = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    matches = re.findall(r"\bpts_time:([+\-\d.eE]+)", p.stderr)
    if p.returncode or not path.is_file() or not matches:
        raise MediaError("focused frame extraction failed or decoded timestamp unavailable")
    actual = float(matches[0])
    if not math.isfinite(actual):
        raise MediaError("invalid decoded frame PTS")
    return actual


def sample_window(video, out_dir, *, start=0.0, end=None, max_frames=16, width=960, crop=None, source_sha=None):
    video, out = Path(video).resolve(), Path(out_dir).resolve()
    if not video.is_file():
        raise ValueError("a local video file is required")
    if out.exists():
        raise ValueError("inspection output exists; choose a new directory")
    if isinstance(max_frames, bool) or not isinstance(max_frames, int) or not 1 <= max_frames <= 64:
        raise ValueError("max_frames must be between 1 and 64")
    if isinstance(width, bool) or not isinstance(width, int) or not 160 <= width <= 1920:
        raise ValueError("width must be between 160 and 1920")
    if crop is not None:
        if len(crop) != 4:
            raise ValueError("crop needs x,y,width,height in 0..1")
        crop = [finite(v, "crop") for v in crop]
        x, y, cw, ch = crop
        if not (0 <= x < 1 and 0 <= y < 1 and cw > 0 and ch > 0 and x + cw <= 1 and y + ch <= 1):
            raise ValueError("crop must stay within the displayed frame")
    info = video_info(video)
    start, end = window(info.duration, start, end)
    verify_source = source_sha is None
    source_sha = source_sha or digest(video)
    # Sample across the complete requested window, rather than truncating its beginning.
    requested = [start + (end - start) * i / max_frames for i in range(max_frames)]
    out.mkdir(parents=True)
    manifest = {"schema": "rea-video.inspection.v1", "source_sha256": source_sha,
                "source": str(video), "duration": info.duration, "scope": {"start": start, "end": end},
                "settings": {"max_frames": max_frames, "width": width, "crop": crop},
                "timestamp_method": "decoded_pts", "frames": [], "failures": [],
                "coverage": "sampled_frames_only", "status": "running"}
    for i, t in enumerate(requested):
        target = out / f"frame_{i + 1:04d}.jpg"
        try:
            actual = extract(video, info, t, target, width, crop)
            if not start - 0.001 <= actual < end:
                raise MediaError("decoded frame is outside the requested window")
            manifest["frames"].append({"id": f"frame_{i + 1:04d}", "requested_time": t, "time": actual,
                                       "path": target.name, "sha256": digest(target)})
        except (MediaError, OSError, subprocess.SubprocessError) as exc:
            manifest["failures"].append({"requested_time": t, "reason": type(exc).__name__})
    times = sorted(set(f["time"] for f in manifest["frames"]))
    manifest["max_sample_gap_seconds"] = max(b - a for a, b in zip([start] + times, times + [end]))
    manifest["returned"] = len(manifest["frames"])
    manifest["status"] = "partial" if manifest["failures"] else "ok"
    if not manifest["frames"]:
        manifest["status"] = "failed"
    if verify_source and digest(video) != source_sha:
        manifest["status"] = "failed"
        manifest["failures"].append({"reason": "source_changed"})
    atomic_json(out / "manifest.json", manifest)
    return manifest


def verified_manifest(path: Path, expected_hash: str):
    if not path.is_file() or digest(path) != expected_hash:
        raise ValueError("chapter manifest changed or is missing")
    m = json.loads(path.read_text(encoding="utf-8"))
    root = path.parent.resolve()
    for frame in m["frames"]:
        p = (root / frame["path"]).resolve()
        if not p.is_relative_to(root) or not p.is_file() or digest(p) != frame["sha256"]:
            raise ValueError("chapter frame changed or is missing")
    return m


def chapter_index(video, output, *, chunk_seconds=600.0, overlap=2.0, max_frames=16, width=960, resume=False):
    video, output = Path(video).resolve(), Path(output).resolve()
    chunk_seconds, overlap = finite(chunk_seconds, "chunk_seconds"), finite(overlap, "overlap")
    if not 1 <= chunk_seconds <= 3600 or not 0 <= overlap < chunk_seconds / 2:
        raise ValueError("chunk must be 1..3600 seconds; overlap must be below half a chunk")
    info = video_info(video)
    if not math.isfinite(info.duration) or info.duration <= 0:
        raise ValueError("invalid source duration")
    key = {"source_sha256": digest(video), "chunk_seconds": chunk_seconds, "overlap": overlap,
           "max_frames": max_frames, "width": width, "version": __version__}
    checkpoint = output / "chapters.json"
    if output.exists() and not resume:
        raise ValueError("chapter output exists; use --resume or a new directory")
    if resume:
        saved = json.loads(checkpoint.read_text(encoding="utf-8"))
        if saved.get("identity") != identity(key):
            raise ValueError("source, settings or tool version changed; choose a new chapter directory")
    else:
        saved = {"schema": "rea-video.chapters.v1", "identity": identity(key), "settings": key,
                 "duration": info.duration, "chapters": [], "status": "running"}
    completed = {c["index"]: c for c in saved["chapters"]}
    if len(completed) != len(saved["chapters"]) or any(type(i) is not int or i < 0 or i >= math.ceil(info.duration / chunk_seconds) for i in completed):
        raise ValueError("invalid chapter checkpoint entries")
    for i in range(math.ceil(info.duration / chunk_seconds)):
        start, end = i * chunk_seconds, min(info.duration, (i + 1) * chunk_seconds)
        if i in completed:
            c = completed[i]
            target = (output / c["manifest"]).resolve()
            if not target.is_relative_to(output):
                raise ValueError("chapter manifest outside index directory")
            m = verified_manifest(target, c["manifest_sha256"])
            if c.get("start") != start or c.get("end") != end or m.get("source_sha256") != key["source_sha256"]:
                raise ValueError("chapter source or time changed")
            if m.get("status") != "ok" or m.get("settings") != {"max_frames": max_frames, "width": width, "crop": None}:
                raise ValueError("chapter settings or status changed")
            if m.get("scope") != {"start": max(0, start - overlap), "end": min(info.duration, end + overlap)}:
                raise ValueError("chapter scope changed")
            continue
        # An interrupted attempt is preserved; resume writes a fresh attempt directory.
        folder = output / f"chapter_{i + 1:04d}_{uuid.uuid4().hex[:8]}"
        m = sample_window(video, folder, start=max(0, start - overlap),
                          end=min(info.duration, end + overlap), max_frames=max_frames, width=width,
                          source_sha=key["source_sha256"])
        if m["status"] != "ok":
            saved["status"] = "partial"
            atomic_json(checkpoint, saved)
            raise MediaError("chapter sampling incomplete; preserved attempt, resume to retry")
        saved["chapters"].append({"index": i, "start": start, "end": end,
                                  "manifest": (folder / "manifest.json").relative_to(output).as_posix(),
                                  "manifest_sha256": digest(folder / "manifest.json"),
                                  "merge_rule": "prefer frames inside chapter [start,end); timestamps are source-relative"})
        atomic_json(checkpoint, saved)
    if digest(video) != key["source_sha256"]:
        raise ValueError("source changed while indexing")
    saved["status"] = "ok"
    atomic_json(checkpoint, saved)
    return saved


def validate_claims(report, manifest_path, transcript_path=None):
    """Validate citation structure/integrity; cannot prove that a claim is semantically true."""
    manifest_path = Path(manifest_path).resolve()
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if report.get("source_sha256") != m["source_sha256"]:
        raise ValueError("claim source mismatch")
    if not isinstance(report.get("claims"), list):
        raise ValueError("claims must be an array")
    frames = {f["id"]: f for f in m["frames"]}
    speech = {}
    if transcript_path:
        from .transcript import load_transcript
        tr = load_transcript(Path(transcript_path), {"sha256": m["source_sha256"], "duration": m["duration"]})
        speech = {s["id"]: s for s in tr["segments"]}
    for claim in report.get("claims", []):
        if not isinstance(claim, dict) or not isinstance(claim.get("text"), str) or not claim["text"].strip():
            raise ValueError("each claim needs non-empty text")
        start, end = window(m["duration"], claim["start"], claim["end"])
        kind, support = claim.get("kind"), claim.get("support")
        if kind not in ("observed", "spoken", "inferred") or support not in ("supported", "conflicted", "not_found"):
            raise ValueError("invalid claim kind/support")
        refs = claim.get("frames", [])
        segments = claim.get("segments", [])
        if not isinstance(refs, list) or not isinstance(segments, list):
            raise ValueError("claim citations must be arrays")
        for ref in refs:
            f = frames.get(ref)
            if f is None or not start <= f["time"] < end:
                raise ValueError("missing/out-of-window frame citation")
            p = (manifest_path.parent / f["path"]).resolve()
            if not p.is_relative_to(manifest_path.parent) or digest(p) != f["sha256"]:
                raise ValueError("frame citation integrity check failed")
        for ref in segments:
            s = speech.get(ref)
            if s is None or not s["start"] < end or not s["end"] > start:
                raise ValueError("missing/out-of-window spoken citation")
        if support != "not_found" and ((kind == "observed" and not refs) or (kind == "spoken" and not segments)
                                      or (kind == "inferred" and not (refs or segments))):
            raise ValueError("claim requires evidence for its modality")
        if kind == "inferred" and not claim.get("uncertainty"):
            raise ValueError("inferred claim requires uncertainty")
    return {"status": "valid", "claims": len(report.get("claims", [])),
            "limit": "citation structure and bytes checked, not semantic truth or actual viewing"}
