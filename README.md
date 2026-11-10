# REA Video Evidence

[English](README.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

A CLI and agent skill for evidence-aware video breakdown: inspect shots, screen text, sound signals and production hypotheses, then retrieve the relevant moments without sending a whole report to your agent.

This is an independently maintained derivative of [JuneYaooo/rea-video](https://github.com/JuneYaooo/rea-video), based on commit `d2fb1e06373a7ecc9379545591ac3904f154b8c9`. It preserves the Apache-2.0 license and upstream credit. See [UPSTREAM.md](UPSTREAM.md) for the exact scope.

## What this edition adds

- **Focused evidence retrieval:** filter an existing breakdown by time or literal keyword; return timestamped JSON with explicit evidence origins.
- **Review queue:** list shots without applied agent review, prioritize uncertainty, and paginate the results.
- **Honest status:** distinguish OCR, tool evidence, agent review, external VLM status, missing images and unrecorded listening verification.
- **Windows Unicode support:** preserve storyboard, element and sticker images when paths contain non-ASCII characters.
- **Portable skill:** install into Codex, Claude Code or another agent's skills folder without overwriting an existing skill.

The underlying shot detection, production classification, OCR, report generation and remake planning come from upstream. Classification scores are hypotheses, not proof of how a video was made.

## New in 0.2

Source-bound reviews reject wrong-source answers and invalid probabilities. OCR has a shared hard call budget and explicit failure states. SRT/VTT import and optional local ASR add spoken-text search. New `doctor`, `inspect`, `chapters --resume` and `validate-claims` commands provide diagnostics, focused evidence and resumable long-video indexing. Full-size shot retention is bounded; English formatting includes the upstream fix.

See [commands, compatibility and limits](docs/workflows.md). Chapters indexes sampled evidence; it does not resume full classification. ASR requires an existing local model and never downloads one. Native report languages remain zh/en.

## Install

Requirements: Python 3.10+, FFmpeg and FFprobe on PATH. Use a dedicated environment; this distribution shares the `rea_video` module and `rea-video` command with upstream.

```sh
git clone https://github.com/teateatea03/rea-video-evidence.git
cd rea-video-evidence
python -m venv .venv
```

Activate it: `source .venv/bin/activate` on macOS/Linux, or `.venv\Scripts\Activate.ps1` in Windows PowerShell. If shell policy blocks activation, call the environment's Python/CLI by its full path instead of changing system policy.

```sh
python -m pip install -e ".[dev]"
rea-video --help
python scripts/install_skill.py --agent codex
```

The Python distribution is named `rea-video-evidence`; the CLI remains `rea-video`. The installer copies only the skill, does not modify PATH or install the CLI, and refuses to overwrite existing destinations. Use `--agent claude`, `--agent agents` or an explicit `--dest` when appropriate.

For optional OCR, install `".[ocr]"`. RapidOCR also requests `opencv-python`, which conflicts with this project's headless OpenCV files. Inside this dedicated environment only:

```sh
python -m pip install -e ".[ocr]"
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall --no-deps "opencv-python-headless>=4.8,<5"
```

After this upstream workaround, `pip check` reports RapidOCR's missing `opencv-python` metadata requirement even though headless supplies `cv2`. Verify actual OCR; do not describe this warning as a clean dependency check.

## Use

```sh
rea-video decompose "reference.mp4" -o "out/reference-01" --no-vlm --lang en
rea-video summary "out/reference-01/breakdown.json"
rea-video evidence "out/reference-01" --start 3.5 --end 8 --limit 4
rea-video evidence "out/reference-01" --query "product" --limit 4
rea-video evidence "out/reference-01" --pending --limit 4
```

`evidence` is read-only: no decoding, model calls, credential loading or persistent memory writes. It searches existing OCR/tool/review text and imported transcript segments, with spoken text separate from screen text. It does not infer unobserved image semantics or run speech recognition during a query. A zero result does not prove absence. Ranges are half-open `[start,end)`; use `pagination.next_offset` with `--offset` to continue.

An agent that can inspect images can run:

```sh
rea-video review "out/reference-01"
# Inspect the actual images and fill only the shots reviewed in review_answers.json.
rea-video apply-review "out/reference-01" --by your-agent
```

Outputs include `report.html`, `report.md`, `breakdown.json`, storyboard and shot images, and available caption/audio artifacts. The first stem separation downloads an approximately 67 MB UVR ONNX model to a local cache. External VLM use is optional, separately configured and may cost money; never put credentials in the repository.

## Limits and validation

Report generation supports `zh` and `en`. These four README translations do not imply Japanese/Korean report-generation support. Agent replies can follow the user's language.

Frame cadence alone does not prove AI origin. OCR is not an ASR transcript. An image file's existence does not establish visual review; audio signals and successful decoding do not establish intelligibility or music provenance. Applied review records describe sampled frames, not continuous viewing. No new classification-accuracy claim is made.

```sh
python -m pytest -q
```

Tests use generated fixtures and isolated memory. No reference videos, user reports, model weights, credentials or machine-specific maintenance logs are shipped.

## Project links and credit

- [GitHub](https://github.com/teateatea03/rea-video-evidence)
- [GitLab.com](https://gitlab.com/angeltea01/rea-video-evidence)
- [Architecture and evidence contract](docs/evidence.md)
- [Installation and agent workflow](skills/rea-video/SKILL.md)
- [Changes](CHANGELOG.md), [contributing](CONTRIBUTING.md), [license](LICENSE), [notice](NOTICE)
- [Upstream authorship and design references](UPSTREAM.md)

A separate local GitLab mirror can be maintained by the owner; its availability depends on the owner's network and access policy.
