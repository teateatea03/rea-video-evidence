"""CLI adapters for evidence acquisition; none loads .env or user preferences."""
import json
from pathlib import Path


def register(sub):
    d = sub.add_parser("doctor", help="Read-only dependency and executable diagnostics")
    d.add_argument("--json", action="store_true", help="JSON output (also the default)")
    d.set_defaults(func=run)
    t = sub.add_parser("transcript", help="Import source-bound SRT/VTT into a report")
    t.add_argument("out_dir")
    t.add_argument("--input", required=True)
    t.add_argument("--origin", default="supplied_subtitles", choices=["manual_subtitles", "automatic_subtitles", "supplied_subtitles"])
    t.add_argument("--language", default="unknown")
    t.set_defaults(func=run)
    a = sub.add_parser("asr", help="Optional local-only ASR; never downloads models")
    a.add_argument("video")
    a.add_argument("-o", "--out", required=True)
    a.add_argument("--model", required=True, help="Local faster-whisper model directory")
    a.add_argument("--language")
    a.set_defaults(func=run)
    for command, help_text in (("inspect", "Bounded focused frames with decoded timestamps"),
                               ("chapters", "Resumable long-video evidence index; no classification")):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("video")
        p.add_argument("-o", "--out", required=True)
        p.add_argument("--max-frames", type=int, default=16)
        p.add_argument("--width", type=int, default=960)
        if command == "inspect":
            p.add_argument("--start", type=float, default=0.0)
            p.add_argument("--end", type=float)
            p.add_argument("--crop", type=float, nargs=4, metavar=("X", "Y", "W", "H"))
        else:
            p.add_argument("--chunk-seconds", type=float, default=600.0)
            p.add_argument("--overlap", type=float, default=2.0)
            p.add_argument("--resume", action="store_true")
        p.set_defaults(func=run)
    v = sub.add_parser("validate-claims", help="Validate claim citations against an inspection manifest")
    v.add_argument("report")
    v.add_argument("--manifest", required=True)
    v.add_argument("--transcript")
    v.set_defaults(func=run)


def run(args):
    from .inspection import sample_window, chapter_index, validate_claims
    from .transcript import import_transcript, transcribe_local
    if args.cmd == "doctor":
        from .doctor import diagnose
        result = diagnose()
    elif args.cmd == "transcript":
        result = import_transcript(args.out_dir, args.input, origin=args.origin, language=args.language)
    elif args.cmd == "asr":
        result = transcribe_local(args.video, args.out, args.model, args.language)
    elif args.cmd == "inspect":
        result = sample_window(args.video, args.out, start=args.start, end=args.end,
                               max_frames=args.max_frames, width=args.width, crop=args.crop)
    elif args.cmd == "chapters":
        result = chapter_index(args.video, args.out, chunk_seconds=args.chunk_seconds,
                               overlap=args.overlap, max_frames=args.max_frames, width=args.width, resume=args.resume)
    else:
        result = validate_claims(json.loads(Path(args.report).read_text(encoding="utf-8")),
                                 args.manifest, args.transcript)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result.get("status") not in ("failed", "partial", "unavailable", "needs_attention") else 2
