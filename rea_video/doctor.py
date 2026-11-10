"""Read-only capability diagnostics. Never reads env files, keys or downloads models."""
from __future__ import annotations
import importlib.metadata
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


def diagnose():
    checks = []
    for tool in ("ffmpeg", "ffprobe"):
        path = shutil.which(tool)
        status, version = "unavailable", None
        if path:
            try:
                p = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
                version = p.stdout.splitlines()[0] if p.stdout else None
                status = "ok" if p.returncode == 0 else "failed"
            except (OSError, subprocess.SubprocessError):
                status = "failed"
        checks.append({"name": tool, "required": True, "status": status, "path": path, "version": version})
    for distribution, module, required in (
        ("numpy", "numpy", True), ("opencv-python-headless", "cv2", True),
        ("Pillow", "PIL", True), ("rapidocr-onnxruntime", "rapidocr_onnxruntime", False),
        ("faster-whisper", "faster_whisper", False)):
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        # Actual imports isolated from this process; does not initialize OCR/ASR engines.
        if importlib.util.find_spec(module) is None:
            checks.append({"name": distribution, "required": required, "status": "unavailable", "version": version})
            continue
        try:
            p = subprocess.run([sys.executable, "-c", f"import {module}"], capture_output=True, timeout=20)
            status = "import_ok" if p.returncode == 0 else "failed"
        except (OSError, subprocess.SubprocessError):
            status = "failed"
        checks.append({"name": distribution, "required": required, "status": status, "version": version,
                       "limit": "import only; model execution not tested"})
    cv = []
    for dist in ("opencv-python", "opencv-python-headless", "opencv-contrib-python", "opencv-contrib-python-headless"):
        try:
            cv.append({"distribution": dist, "version": importlib.metadata.version(dist)})
        except importlib.metadata.PackageNotFoundError:
            pass
    ready = all(c["status"] in ("ok", "import_ok") for c in checks if c["required"])
    return {"schema": "rea-video.doctor.v1", "status": "ready" if ready and len(cv) <= 1 else "needs_attention",
            "python": sys.executable, "module": str(Path(__file__).resolve().parent),
            "cli": shutil.which("rea-video"), "checks": checks, "opencv_distributions": cv,
            "opencv_conflict": len(cv) > 1, "external_services": "not_contacted",
            "models": "not_initialized_or_downloaded",
            "repair_hint": "Use the dedicated environment and README OpenCV workaround; no automatic changes were made."}
