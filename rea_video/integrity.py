"""Stable source/review identities and atomic checkpoint writes."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path


def digest(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def identity(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def atomic_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def binding(b: dict, root: str | Path | None = None) -> dict:
    source = b["source"]
    layout = [{"id": r["id"], "start": r["start"], "end": r["end"],
               "assets": r.get("assets", {})} for r in b["shots"]]
    core = {"source": {k: source.get(k) for k in ("sha256", "sha256_head", "filename", "duration")},
            "shots": layout, "tool": b.get("tool"), "schema": b.get("schema")}
    result = {"schema": "rea-video.review-binding.v1", "analysis_id": identity(core),
              "source_sha256": source.get("sha256"), "images": {}}
    if root is not None:
        root = Path(root).resolve()
        for r in b["shots"]:
            for name, relative in r.get("assets", {}).items():
                if not isinstance(relative, str):
                    raise ValueError("invalid review asset path")
                p = (root / relative).resolve()
                if not p.is_relative_to(root):
                    raise ValueError("review asset outside report")
                result["images"][f"{r['id']}:{name}"] = digest(p) if p.is_file() else None
    return result


def validate_binding(b: dict, answers: dict, root=None, allow_legacy=False) -> str:
    supplied = answers.get("binding")
    if supplied is None:
        if not allow_legacy:
            raise ValueError("unbound legacy review: regenerate review in a new folder, or explicitly use --allow-legacy")
        return "legacy_unbound"
    if not isinstance(supplied, dict):
        raise ValueError("invalid review binding")
    expected = binding(b, root)
    for key in ("schema", "analysis_id", "source_sha256"):
        if supplied.get(key) != expected[key]:
            raise ValueError("review source or shot layout does not match this analysis")
    if root is not None:
        if supplied.get("images") != expected["images"]:
            raise ValueError("review images changed since the template was created")
        source = Path(b["source"].get("path", ""))
        if source.is_file() and b["source"].get("sha256") and digest(source) != b["source"]["sha256"]:
            raise ValueError("source video changed since analysis")
    return "bound" if b["source"].get("sha256") else "bound_legacy_source"
