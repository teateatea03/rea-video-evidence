# Modified in rea-video-evidence on 2026-11-10; see UPSTREAM.md.
"""Bounded, time-addressed evidence handoff from an existing breakdown.

No model calls, decoding, persisted memory or changes to analysis results.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PureWindowsPath

from .review import _priority
from bisect import bisect_left, bisect_right


class IntervalIndex:
    """Sorted starts and prefix maximum ends; works with overlapping intervals."""
    def __init__(self, rows, start="t0", end="t1"):
        self.start, self.end = start, end
        self.rows = sorted(({**r, start: _number(r.get(start), start), end: _number(r.get(end), end)} for r in rows), key=lambda r: r[start])
        self.starts, self.ends = [], []
        for row in self.rows:
            a, b = _number(row.get(start), start), _number(row.get(end), end)
            if a < 0 or b <= a:
                raise ValueError("invalid evidence interval")
            self.starts.append(a)
            self.ends.append(max(b, self.ends[-1] if self.ends else b))

    def overlap(self, start, end):
        lo, hi = bisect_right(self.ends, start), bisect_left(self.starts, end)
        return [r for r in self.rows[lo:hi] if r[self.end] > start]


def _number(value, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number") from None
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _excerpt(value, query: str = "", size: int = 240) -> str:
    text = str(value or "")
    at = text.casefold().find(query.casefold()) if query else -1
    start = max(0, at - 60) if at >= 0 else 0
    return ("…" if start else "") + text[start:start + size] + ("…" if len(text) > start + size else "")


def _asset(root: Path, relative) -> dict:
    if not isinstance(relative, str) or not relative:
        return {"path": None, "status": "not_recorded"}
    path = Path(relative)
    if path.is_absolute() or PureWindowsPath(relative).drive or ".." in PureWindowsPath(relative).parts:
        return {"path": None, "status": "outside_report"}
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        return {"path": None, "status": "outside_report"}
    return {"path": str(resolved), "status": "available" if resolved.is_file() else "missing"}


def _has_review(rec: dict) -> bool:
    probs = (rec.get("review") or {}).get("label_probs") or {}
    return bool(probs) and any(isinstance(v, (int, float)) and not isinstance(v, bool)
                               and math.isfinite(v) and v > 0 for v in probs.values())


def _search_items(rec: dict, text: list[dict], speech=()):
    base, det, review = rec.get("base") or {}, rec.get("deterministic") or {}, rec.get("review") or {}
    yield "shot_id", rec["id"]
    yield "classification", base.get("label", "")
    yield "agent_review", review.get("description", "")
    for value in det.get("evidence") or []:
        yield "measurement", value
    for value in review.get("evidence") or []:
        yield "agent_review", value
    for cue in text:
        yield "screen_text", cue.get("text", "")
    for segment in speech:
        yield "spoken", segment.get("text", "")


def evidence_pack(path: str | Path, *, start: float = 0.0, end: float | None = None,
                  query: str = "", pending: bool = False, limit: int = 8, offset: int = 0) -> dict:
    """Return overlapping shots in [start, end), with explicit output/coverage bounds."""
    start = _number(start, "start")
    if start < 0:
        raise ValueError("start must be non-negative")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError("query must be at most 200 characters")
    path = Path(path).expanduser().resolve()
    if path.is_dir():
        path = path / "breakdown.json"
    raw = path.read_bytes()
    b = json.loads(raw)
    if not isinstance(b, dict) or not isinstance(b.get("source"), dict) or not isinstance(b.get("shots"), list):
        raise ValueError("expected a rea-video breakdown with source and shots")
    duration = _number(b["source"].get("duration"), "source.duration")
    if duration <= 0:
        raise ValueError("source.duration must be positive")
    end = duration if end is None else _number(end, "end")
    if not start < end <= duration:
        raise ValueError("require 0 <= start < end <= source duration")
    root = path.parent
    cues = (b.get("packaging") or {}).get("text_cues") or []
    context = b.get("video_context") or {}
    from .transcript import load_transcript
    transcript = load_transcript(root / "transcript.json", b["source"])
    speech_index = IntervalIndex(transcript["segments"], "start", "end")
    text_index = IntervalIndex(cues)
    window, seen = [], set()
    for rec in b["shots"]:
        sid = rec.get("id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("shot ids must be non-empty and unique")
        seen.add(sid)
        t0, t1 = _number(rec.get("start"), "shot.start"), _number(rec.get("end"), "shot.end")
        if not 0 <= t0 < t1 <= duration + 0.001:
            raise ValueError(f"invalid shot range: {rec.get('id')}")
        if t0 < end and t1 > start:
            priority, why = _priority(rec, context)
            window.append((rec, priority, why))
    matched = []
    for rec, priority, why in window:
        reviewed = _has_review(rec)
        if pending and reviewed:
            continue
        # OCR is screen text, never an ASR transcript. Associate by time overlap.
        text = text_index.overlap(max(start, rec["start"]), min(end, rec["end"]))
        speech = speech_index.overlap(max(start, rec["start"]), min(end, rec["end"]))
        if query and not any(query.casefold() in str(value).casefold() for _, value in _search_items(rec, text, speech)):
            continue
        matched.append((rec, priority, why, text, speech))
    if pending:
        matched.sort(key=lambda row: (row[1] != "high", row[0]["start"], row[0]["id"]))
    else:
        matched.sort(key=lambda row: (row[0]["start"], row[0]["id"]))
    rows = []
    for rec, priority, why, text, speech in matched[offset:offset + limit]:
        base, det, review = rec.get("base") or {}, rec.get("deterministic") or {}, rec.get("review") or {}
        assets = rec.get("assets") or {}
        speech = sorted(speech, key=lambda s: (not (query and query.casefold() in s["text"].casefold()), s["start"], s["id"]))
        ordered_text = sorted(text, key=lambda c: (not (query and query.casefold() in str(c.get("text", "")).casefold()),
                                                  c.get("t0", 0), str(c.get("id", ""))))
        rows.append({
            "id": rec["id"], "citation": f"{rec['id']}@{rec['start']:.3f}-{rec['end']:.3f}s",
            "start": rec["start"], "end": rec["end"],
            "priority": priority, "review_reasons": [_excerpt(reason) for reason in why[:8]],
            "classification": {"label": base.get("label"), "score": base.get("confidence"),
                               "uncertain": _excerpt(base.get("uncertain")), "disputed": _excerpt(base.get("disputed")),
                               "user_corrected": base.get("decided_by") == "user"},
            "agent_review": {"applied": _has_review(rec), "by": _excerpt(review.get("_by"), size=80),
                             "description": _excerpt(review.get("description"), query),
                             "evidence": [_excerpt(e, query) for e in (review.get("evidence") or [])[:4]]},
            "spoken": {"origin": transcript.get("origin"), "language": transcript.get("language"),
                       "total": len(speech), "truncated": len(speech) > 8,
                       "items": [{**s, "text": _excerpt(s["text"], query)} for s in speech[:8]]},
            "measured_evidence": [_excerpt(e, query) for e in (det.get("evidence") or [])[:4]],
            "query_matches": [{"origin": origin, "text": _excerpt(value, query)}
                              for origin, value in _search_items(rec, text, speech)
                              if query and query.casefold() in str(value).casefold()][:4],
            "images": {name: _asset(root, assets.get(name)) for name in ("sheet", "first_frame", "last_frame", "strip")},
            "screen_text": {"total": len(text), "returned": min(8, len(text)),
                            "truncated": len(text) > 8,
                            "items": [{"id": c.get("id"), "start": c.get("t0"), "end": c.get("t1"),
                                       "kind": c.get("kind"), "text": _excerpt(c.get("text"), query)} for c in ordered_text[:8]]},
        })
    return {
        "schema": "rea-video.evidence.v1", "breakdown": str(path),
        "breakdown_sha256": hashlib.sha256(raw).hexdigest(),
        "source": {k: b["source"].get(k) for k in ("path", "filename", "duration", "sha256", "sha256_head")},
        "scope": {"start": start, "end": end, "query": query, "pending_only": pending},
        "coverage": {"window_shots": len(window),
                     "applied_review_shots": sum(_has_review(r) for r, _, _ in window),
                     "unreviewed_high_priority": sum(p == "high" and not _has_review(r) for r, p, _ in window)},
        "pagination": {"matched": len(matched), "returned": len(rows), "offset": offset, "limit": limit,
                       "next_offset": offset + len(rows) if offset + len(rows) < len(matched) else None,
                       "truncated": len(rows) < len(matched)},
        "vlm_status": (b.get("analysis") or {}).get("vlm", {}).get("status", "not_recorded"),
        "transcript_status": transcript["status"],
        "ocr_status": (b.get("analysis") or {}).get("ocr_details", {}).get("status", "not_recorded"),
        "timestamp_status": (b.get("analysis") or {}).get("timestamps", {"status": "not_recorded"}),
        "audio": {"signal_analysis_present": bool(b.get("audio")),
                  "has_audio": (b.get("audio") or {}).get("has_audio"),
                  "stems_status": "produced" if (b.get("stems") or {}).get("ok") else "unavailable_or_skipped",
                  "listening_verification": "not_recorded"},
        "shots": rows,
        "limits": ["Applied review records describe sampled-frame review, not continuous visual coverage.",
                   "Screen text is OCR, not a verified speech transcript.",
                   "Available image paths are existence checks, not visual verification.",
                   "Classification scores and provenance hints do not prove production origin."],
    }
