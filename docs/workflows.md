# Evidence workflows (0.2)

## Review identity and compatibility

New decompose reports include the full source SHA-256. New review templates bind the source, stable shot layout/tool version and image digests. Applying answers checks this binding before changing the report; when the source still exists its current full hash is checked too. Missing or changed images fail validation. A hash checks identity, not whether someone actually viewed an image.

Fill only inspected shots, retain the template binding and time fields, and provide concrete evidence. Probabilities must be finite, non-negative numbers with a positive sum; booleans, NaN and infinity are rejected. Duplicate shot IDs reject the file. Invalid individual answers are listed as skipped. Previous applied answers are retained in review_history when replaced.

Old unbound answers are rejected by default. Preserve them and generate a fresh template in a separate report copy, or explicitly use apply-review --allow-legacy. That override is recorded as legacy_unbound, never as verified source identity. Reports without a full source hash remain bound_legacy_source; re-analyze for full identity. Partial batch review does not invalidate the unchanged source/layout binding.

## OCR and diagnostics

The whole-video pass and per-shot fallback share a maximum of 240 actual OCR calls. Cached results do not spend a call. Long videos use sparser whole-video sampling; short text may be missed. analysis.ocr_details separates calls, failures, scanned/reused frames, budget exhaustion and off/unavailable/failed/partial/ok/not_run. These describe execution, not complete text coverage. No text found is different from no successful OCR.

~~~sh
rea-video doctor --json
~~~

Doctor identifies the running Python/module/CLI, executes FFmpeg/FFprobe version checks and isolated package imports, and lists conflicting OpenCV distributions. It does not load env files, initialize models, contact services or repair the environment. An import is not model validation. Optional ASR absence can be reported separately from base readiness.

## Subtitles and local ASR

~~~sh
rea-video transcript out/reference-01 --input captions.srt --origin manual_subtitles --language zh
rea-video evidence out/reference-01 --query "spoken phrase" --limit 4
~~~

SRT and VTT are UTF-8; retain original time offsets and language. Imports reject invalid/out-of-range times and refuse to overwrite transcript.json. The new sidecar is bound to the report's full source hash. Evidence queries read it without writing, decoding or invoking a model. Overlap lookup uses a sorted interval index; the original breakdown JSON is still loaded in memory.

Spoken text is separate from screen_text. Manual/supplied/automatic subtitles and ASR are statements or recognition results, not proof of visible events or verified listening. Translation and recognition can be wrong. Recheck names, numbers and consequential claims against original audio.

Optional ASR installation in the dedicated environment:

~~~sh
python -m pip install -e ".[asr]"
rea-video asr reference.mp4 --model /absolute/local/faster-whisper-model -o out/reference-01/transcript.json --language zh
~~~

The model must be an existing local CTranslate2 directory containing model.bin, config.json and tokenizer.json. Requiring a local tokenizer prevents the backend from fetching its fallback tokenizer. CPU int8 and local_files_only are enforced. No model name downloads or paid endpoints are accepted. Missing runtime/model/audio is reported explicitly; the CLI does not silently fall back to cloud ASR. Automatic ASR language detection is available by omitting --language; this is distinct from OCR/report language support. ASR execution metadata records model version and weight hash; output remains unverified_text_not_listening.

## Focused frames and long videos

~~~sh
rea-video inspect reference.mp4 -o out/focus-01 --start 3.5 --end 8 --max-frames 12 --width 1280
rea-video inspect reference.mp4 -o out/text-01 --start 3.5 --end 5 --max-frames 4 --width 1280 --crop 0 0.6 1 0.4
rea-video chapters long.mp4 -o out/long-index --chunk-seconds 600 --overlap 2 --max-frames 16
rea-video chapters long.mp4 -o out/long-index --chunk-seconds 600 --overlap 2 --max-frames 16 --resume
~~~

Inspect writes a new folder with bounded image count (1–64), width (160–1920), requested and decoded source-relative PTS, image hashes, failures and maximum sample gap. Crop uses displayed-frame x/y/width/height fractions in 0..1. Sampling spans the requested window instead of only its beginning. Failed or out-of-window frames are recorded, not labeled as success. Keep all old attempts.

Start with an overview; densify only action timing, small text, conflicts or a user-requested interval. Inspect the actual output frames before recording observations. Sampled frames do not establish continuous motion.

Chapters is a lightweight evidence index, not a replacement classification pipeline. It processes a chapter at a time, checkpoints atomically after each completed chapter, and resumes only matching source/settings/tool versions. Completed manifests and image hashes are verified before reuse. Interrupted attempt folders are preserved; retries use new folders. Original timestamps are retained. In overlap regions, merge by the chapter's own half-open [start,end) window to avoid duplicate observations. It does not generate merged semantic summaries or invoke agents automatically.

Full decompose retains only a bounded set of template samples and the current shot instead of all shots' full-sized frames. It still scans the full stream and retains small detection thumbnails; use chapters for long-video overview work. No full decompose stage-resume or constant-memory claim is made.

analysis.timestamps distinguishes packet-aligned CFR, packet PTS and estimated index/fps fallback with a reason. Inspect uses decoded frame PTS; precision depends on source timestamps. Partial decoder errors now fail explicitly.

## Claim citations

Create claims.json only from inspected evidence:

~~~json
{
  "source_sha256": "copy the source hash from manifest.json",
  "claims": [{
    "text": "A card is visible.",
    "start": 3.5,
    "end": 8,
    "kind": "observed",
    "support": "supported",
    "frames": ["frame_0001"],
    "segments": [],
    "uncertainty": ""
  }]
}
~~~

~~~sh
rea-video validate-claims claims.json --manifest out/focus-01/manifest.json
~~~

Kinds: observed, spoken, inferred. Support: supported, conflicted, not_found.
Observed claims require frame citations; spoken claims require segment citations and --transcript; inferred claims require evidence and an uncertainty explanation. The validator checks source identity, ranges, frame membership and image digests. It validates citation structure and bytes, not semantic truth, actual viewing or listening.

## Research and limits

Design references: [watch-video protocol](https://github.com/TomGranot/watch-video/blob/9492ba334de083ba0d74a5bbac18ae6a20ace500/skills/watch-video/references/analysis-protocol.md), [Video Analysis Skill](https://github.com/bydfi-official/video-analysis-skill/blob/b2702695f6fdb50457c30e6483af4f4d6240afa7/README.md), [Video Understanding chapter workflow](https://github.com/Gang-of-Beads/video-understanding-skill/blob/5430cfbb6d072361de21b335e9dc19c6bf010b04/SKILL.md).
No code was copied from these projects. English report formatting incorporates upstream a82fcacf with attribution in UPSTREAM.md. No classification weights or cut thresholds were tuned, and no new accuracy, ASR quality or long-video speed claim is made.
