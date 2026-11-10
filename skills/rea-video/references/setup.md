# Installation and optional VLM

Modified for rea-video-evidence, 2026-11-08. See [upstream attribution](https://github.com/teateatea03/rea-video-evidence/blob/main/UPSTREAM.md).

## CLI and skill

Use Python 3.10+ and FFmpeg/FFprobe on PATH. Clone this edition, create a dedicated venv, activate it or call its Python by full path, then:

```sh
python -m pip install -e ".[dev]"
rea-video --help
rea-video doctor --json
python scripts/install_skill.py --agent codex
```

Use `--agent claude`, `--agent agents` or an explicit `--dest` as needed. Existing destinations are never overwritten. Keep the current installation or back it up explicitly before replacing it. The script installs the skill only; CLI installation is separate. This distribution shares the module and CLI names with upstream, so do not install both into one environment.

Optional OCR:

```sh
python -m pip install -e ".[ocr]"
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
```

Apply that workaround only inside this dedicated environment. RapidOCR metadata still requires opencv-python, so pip check retains a known warning; actual OCR must be verified. Do not silently install conflicting cv2 distributions to hide it.

Windows: use PowerShell and UTF-8 (`PYTHONUTF8=1` for the Python process where needed). Unicode image paths are supported by this edition. If a shell blocks venv activation, call `.venv/Scripts/rea-video.exe` directly; do not weaken system execution policy.

## Optional external model

Run `decompose --no-vlm` when no external service is configured/authorized. This prevents a saved preference from silently enabling it. An image-capable agent can review sampled frames without an external VLM.

Configuration uses an OpenAI-compatible interface:
1. `REA_VLM_BASE_URL`, `REA_VLM_API_KEY`, `REA_VLM_MODEL` (comma-separated model fallbacks supported).
2. Upstream also recognizes capsule-cinema's VIDEO_ANALYSIS_* or GEMINI3_* configuration.

Use `--env-file` for a private file provided by the user. Do not open it to display its contents, commit it, or put credentials in reports/chat. Ask only for a genuinely missing service decision; existing authorization remains valid.

Verify actual status in `analysis.vlm.status`: ok, partial, failed, not_configured or off. A successful request is not proof of correct interpretation. Agent frame review is separate from external VLM execution, and a vision endpoint does not imply audio support. Only claim listening when the service actually supports and processed that audio, or playback was performed.

Tool reports support zh/en. Reply in the user's language; document translated files when producing additional report languages. Never present README translations as native Japanese/Korean report support.
