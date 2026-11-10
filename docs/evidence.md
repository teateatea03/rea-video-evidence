# Evidence retrieval contract

`rea-video evidence REPORT_OR_BREAKDOWN` reads an existing report and emits one UTF-8 JSON document. It does not decode media, call a model, read .env/preferences, alter the report or persist user memory.

## Selection

- `--start` and `--end` are finite seconds in the source timeline, within its duration.
- A shot is selected when it overlaps the half-open interval `[start,end)`; original shot times are retained.
- `--query` performs a case-insensitive literal substring search, up to 200 characters, over shot IDs, classifications, existing tool evidence, applied review descriptions/evidence overlapping OCR text and source-bound imported transcript segments.
- OCR is screen text, not ASR. Search failure does not prove content absence.
- `--pending` excludes records with applied agent-review probabilities and orders existing high-priority cases first. It does not claim that stored review was honestly performed.
- Default page size is 8 shots; `--limit` accepts 1–100, `--offset` is non-negative. Follow `pagination.next_offset` until null.

## Output

The versioned schema is `rea-video.evidence.v1`.

- `breakdown_sha256` binds the precise input JSON bytes, not the whole source video. A changed report produces another snapshot hash.
- `source.sha256` is the full source identity in new reports; `source.sha256_head` is retained for legacy partial-file hashes. Transcript sidecars must match the full hash.
- `coverage` counts all shots in the time window before query/pending filtering, with actual per-shot review records.
- `pagination` separately reports matched and returned shots, omitted results and next offset.
- Each shot contains an ID/time citation, classification hypothesis, review priority, source-tagged query excerpts, applied review, tool evidence, image references up to 8 OCR items and a separate bounded spoken-text list. Query-matching speech segments are prioritized. `transcript_status`, `ocr_status` and `timestamp_status` describe availability and execution, not semantic truth.
- Images have `available`, `missing`, `not_recorded` or `outside_report` status. Absolute or escaping image references are rejected; existence checks apply only to returned images and do not validate their contents.
- `vlm_status` remains separate from agent review. Audio signal analysis and stem production are separate from `listening_verification=not_recorded`.
- Text excerpts are bounded; inspect the full source report for details. An ellipsis or truncation field means material was omitted.

Malformed input, duplicate shot IDs, invalid time ranges and invalid limits fail with exit 2. File-read errors also fail rather than manufacturing evidence.

## Review loop

Retrieve a relevant page, inspect the actual images, and fill only reviewed shots in the existing review_answers.json. Apply the review, then query again against the updated JSON snapshot. Stored review counts and file availability are workflow facts, not a provenance certificate or proof of full-video coverage.

PowerShell 5 users should save JSON with an explicit UTF-8 output encoding, or preserve stdout bytes from a subprocess; bare redirection may write UTF-16.
