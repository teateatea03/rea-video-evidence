# Upstream, attribution and modification record

REA Video Evidence is an independently maintained derivative of:
- Project: [JuneYaooo/rea-video](https://github.com/JuneYaooo/rea-video)
- Baseline: [d2fb1e06373a7ecc9379545591ac3904f154b8c9](https://github.com/JuneYaooo/rea-video/tree/d2fb1e06373a7ecc9379545591ac3904f154b8c9)
- Original copyright: Copyright 2026 JuneYaooo
- License: Apache-2.0; the original LICENSE and NOTICE are retained.

This edition is maintained by [teateatea03](https://github.com/teateatea03). It is not presented as the upstream author's official release.

## Changes made on 2026-11-08

Modified upstream runtime files:
- `rea_video/util.py`: Unicode-safe image read/write helpers and explicit write failures.
- `rea_video/cli.py`: evidence command, options and read-only route; Unicode image helper use.
- `rea_video/motion.py`, `packaging.py`, `pipeline.py`, `production.py`, `remake.py`: replace direct OpenCV path-based image I/O.
- `pyproject.toml`: distinct distribution name, project description and repository links.

Added `rea_video/evidence.py` and regression tests for Unicode image I/O, bounded evidence retrieval and the non-overwriting skill installer. The public skill is adapted from upstream and the local evidence-workflow improvements. Modified references include setup, review, audio, memory and output guidance; the evidence reference is new. Machine-specific paths and maintenance records were removed.

New project-level material includes four README languages, the installer, contribution/change documentation, CI definitions and packaging rules. The module and command names remain `rea_video` and `rea-video` for compatibility, while the distribution is `rea-video-evidence`. Install separately from upstream.

Production classification rules, fusion weights and shot-detection algorithms were not tuned in this edition. Existing model capability tables are inherited data, not a guarantee that a provider or agent host exposes a given feature.

## Design research

The evidence handoff was informed by these public designs; no code from these projects was copied:
- [Hypit: timed reference analysis](https://github.com/hypit-ai/hypit/blob/2d31e88765e297f0795348b460c77a6067f12261/docs/guide/skill.md)
- [Grounded Video Agent: evidence integrity and coverage](https://github.com/sensniu/grounded-video-agent/blob/fea84c8ccc7f2b77ce1abbc391f0177df282483b/src/grounded_video_agent/agent/verification/verifier.py)
- [timecode-agent: verification priority](https://github.com/mupozg823/timecode-agent/blob/02f7c5a9ce1c09b4ba49177d2a4dc8e9ee1bbc03/src/video_agent/verify_priority.py)
- [Open Vision: scoped JSON/frame handoff](https://github.com/michielhdoteth/openvision/blob/084d02957516cd55dd53eee1a6ba720c6f64100a/README.md)
- [PySceneDetect: adaptive cut detection](https://github.com/Breakthrough/PySceneDetect/blob/f1ae68409725440fc406acd76f1ea78a3128d99a/scenedetect/detectors/adaptive_detector.py), studied but not transplanted.

## Changes made on 2026-11-10 (0.2.0)

Added integrity, OCR-budget, transcript, inspection, diagnostic and CLI adapter modules and regression tests. Modified review input validation/binding/history; shared OCR budgeting and status in packaging/overlay/pipeline; bounded retained full-size shot samples; full source hashes; indexed OCR/spoken retrieval; timestamp fallback metadata and decode error checks in media/shots; optional ASR packaging and CLI routes. Updated the skill, four READMEs and evidence workflow documentation.

Ported upstream [a82fcacf016b0bb584c7a5e9d74ed950b6a37ace](https://github.com/JuneYaooo/rea-video/commit/a82fcacf016b0bb584c7a5e9d74ed950b6a37ace), by Christopher Pruijsen and JuneYaooo, for English formatting in i18n/plan/probe/production/report and its regression tests. Apache-2.0 credit is retained. New workflow designs also reference the SHA-pinned sources in docs/workflows.md; no code from those separate projects was copied. No classification weights or shot-detection thresholds were changed.

## Distribution boundaries

Upstream reference videos, case GIFs, user outputs, local logs, credentials, caches and model weights are not included. Tests generate their own fixtures. Optional third-party model downloads remain separate assets with their own terms. See [validation notes](docs/validation.md) for what was actually tested.
