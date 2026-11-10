# Validation and limits

## Reproduce

Use Python 3.12, FFmpeg/FFprobe and a dedicated environment. Install `".[ocr,dev]"` and apply the README's headless OpenCV workaround, then run:

```sh
python -m pytest -q
python scripts/validate_capabilities.py
```

The 0.2 release suite contains 242 tests: the 208 original/upstream/evidence/installer cases, two upstream English regressions and 32 hardening/edge cases. Tests generate media locally and isolate `REA_VIDEO_HOME`; they do not require a paid VLM. GitHub CI exercises Linux and Windows; GitLab CI requires an available runner.

The installer checks include a Unicode destination, an existing destination that must remain untouched, CODEX_HOME routing and rejection of recursive copies. Unicode image tests cover actual element-image production as well as round trips and failure behavior.

## 0.2 validation (2026-11-10)

A fresh dedicated Python 3.12 environment passed all 242 tests. After requiring a complete local ASR tokenizer/config to prevent backend fallback downloads, the affected 32 hardening/edge tests passed again. The wheel built successfully and the skill validator passed.

Real CLI smoke outside the repository covered doctor, silent generated-video decompose, Unicode SRT import and spoken search, decoded-PTS focused sampling, a ten-minute synthetic video's five chapter indexes and verified resume. A rendered OCR card was recognized by actual RapidOCR with a one-call budget. These are functional checks, not general video/ASR/classification accuracy or speed benchmarks. Model bindings were tested with an isolated ASR adapter; no real ASR weights or speech transcription, paid VLM, listening review or hour-long memory benchmark was run.

Four project-owned routing cases are in eval/promptfooconfig.yaml. Run qtools eval eval/promptfooconfig.yaml only with an explicitly selected PROMPTFOO_PROVIDER and a bounded provider budget. No provider-backed evaluation was run for this release, so model routing quality remains unmeasured; schema/fixture tests do not substitute for it.

## Observed 0.1 local checks before packaging

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
