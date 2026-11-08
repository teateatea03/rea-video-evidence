# Validation and limits

## Reproduce

Use Python 3.12, FFmpeg/FFprobe and a dedicated environment. Install `".[ocr,dev]"` and apply the README's headless OpenCV workaround, then run:

```sh
python -m pytest -q
python scripts/validate_capabilities.py
```

The release suite includes 204 upstream/evidence tests plus four installer tests. Tests generate media locally and isolate `REA_VIDEO_HOME`; they do not require a paid VLM. GitHub CI exercises Linux and Windows; GitLab CI requires an available runner.

The installer checks include a Unicode destination, an existing destination that must remain untouched, CODEX_HOME routing and rejection of recursive copies. Unicode image tests cover actual element-image production as well as round trips and failure behavior.

## Observed local checks before packaging

On one 19-second, 10-shot upstream sample:
- Unicode image I/O previously left the storyboard missing and 78 JSON image references unresolved; the fix produced the storyboard, five element sheets and three sticker images, with no unresolved references in that run.
- Bounded evidence retrieval returned the requested reviewed shot and the correct remaining review queue.
- A focused evidence payload was 5672 UTF-8 bytes versus 363612 bytes for the complete breakdown, approximately 98.4% smaller.
- The retrieval smoke check left all 129 existing report files unchanged.

These are a functional smoke check and one output-size comparison, not an independent video-classification benchmark, model-quality result or general speed/cost guarantee. The reference media and local reports are not redistributed.

## Evidence boundaries

Stored agent review does not prove that an agent actually inspected an image. Existence of an output file does not prove its content is correct. Sampling a shot does not establish continuous viewing, and an audio waveform or decode pass does not establish intelligibility. Classification and source guesses retain uncertainty.

Native report generation supports zh/en. Four README languages describe the same functionality; they do not add native Japanese/Korean report generation.

RapidOCR's metadata warning after the headless workaround is known and documented. No paid external VLM, automatic generation, provider compatibility or new classification accuracy was validated for this edition.

Preserve the exact commit and environment when reporting a regression. Do not submit private media or credentials in an issue.
