import argparse
import sys

from . import classify, load, render


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m fltrial", description="Amazon catalog exceptions prototype (mock data only).")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="classify fixtures and write report, packets and raw copies")
    run.add_argument("--approved", default="fixtures/approved.csv")
    run.add_argument("--observations", default="fixtures/observations.csv")
    run.add_argument("--submissions", default="fixtures/submissions.csv")
    run.add_argument("--as-of", help="UTC time, e.g. 2026-10-26T12:00:00Z (default: newest observed_at)")
    run.add_argument("--out", default="out")
    args = parser.parse_args(argv)

    approved = load.read_csv(args.approved)
    observations = load.read_csv(args.observations)
    submissions = load.read_csv(args.submissions)
    if args.as_of:
        as_of = classify.parse_ts(args.as_of)
    else:
        as_of = max(classify.parse_ts(o["observed_at"]) for o in observations if o["observed_at"])

    rows = classify.classify_all(approved, observations, submissions, as_of)
    render.write_outputs(args.out, rows, as_of, [args.approved, args.observations, args.submissions])
    packets = sum(1 for r in rows if r["packet"])
    print(f"as of {classify.fmt_ts(as_of)}: {len(rows)} rows, {packets} packets -> {args.out}/report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
