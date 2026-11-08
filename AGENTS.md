# REA Video Evidence

- Python 3.10+; FFmpeg and FFprobe must be on PATH.
- Install in a dedicated environment: `python -m pip install -e ".[ocr,dev]"`. Follow README's headless OpenCV workaround when OCR installs the conflicting distribution.
- Run `python -m pytest -q`. Fixtures are synthetic and memory is isolated.
- CLI: `python -m rea_video.cli --help`; `evidence` must remain read-only, bounded and credential-free.
- Keep tool evidence, OCR, agent review and external VLM status distinct. Do not turn scores, file existence or cached review counts into provenance/coverage guarantees.
- Skills live in `skills/rea-video`; the public installer never overwrites a destination.
- Maintain equivalent English, Traditional Chinese, Japanese and Korean READMEs. Native tool report languages remain zh/en.
- Preserve LICENSE, NOTICE and UPSTREAM.md. Mark changes to upstream files and retain credit.
- Do not commit media, generated reports, weights, credentials, private paths or local maintenance records. Run a credential scan before publishing.
- Changes to classification rules require independent labeled-video evaluation in addition to unit tests; do not claim accuracy improvements from fixtures.
