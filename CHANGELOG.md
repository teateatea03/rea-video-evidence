# Changelog

## 0.2.0 — 2026-11-10

- Bind new review templates to source/layout/images; reject invalid probability inputs and record explicit legacy compatibility.
- Share a hard OCR call budget across whole-video and shot fallback; expose execution/coverage gaps.
- Import SRT/VTT and retrieve source-bound spoken text separately from OCR; add optional local-only ASR.
- Add read-only doctor, decoded-PTS focused sampling, resumable chapter evidence indexes and claim citation validation.
- Bound retained full-size shot samples; index overlapping evidence intervals; report timestamp fallback and decode errors.
- Port upstream a82fcacf English report formatting and tests. Classification rules and cut thresholds remain unchanged.
- Update the portable skill and documentation in four languages. See docs/workflows.md for compatibility and limits.

## 0.1.0 — 2026-11-08

Initial independently maintained REA Video Evidence release, based on JuneYaooo/rea-video commit d2fb1e06373a7ecc9379545591ac3904f154b8c9.

- Add time/keyword-scoped evidence retrieval, pagination, review queue, source-tagged excerpts and report snapshot hashes.
- Separate applied review, VLM execution, OCR and unrecorded listening verification.
- Fix Windows Unicode image reads/writes and prevent silent missing-image success.
- Package a portable agent skill with a non-overwriting cross-platform installer.
- Add English, Traditional Chinese, Japanese and Korean project documentation.
- Retain upstream classification and shot-detection behavior; make no new accuracy claim.
