"""report.md / report.json, evidence packets and the human-only support draft."""
import json
import shutil
from pathlib import Path

from . import load
from .classify import FRESHNESS_HOURS, HUMAN_REVIEW, PROCESSING_WINDOW_HOURS, fmt_ts

DRAFT_MARK = "DRAFT — for a human to review and send"
OUT_MARKER = ".fltrial-out"
OUT_MARKER_TEXT = "Created by fltrial. fltrial may rewrite report files and clear packets/ and raw/ in this folder.\n"


class OutDirError(Exception):
    pass

ASSUMPTIONS = [
    "Normalization is for comparison only: trim, collapse inner whitespace, Unicode NFKC, casefold; "
    "`int` attributes compare numerically (`2` == `2.0`). No synonym mapping. Raw values are always shown.",
    "`UNKNOWN`, empty, `None` or a missing row means no observation, never a mismatch. "
    "Rows without `observed_at` are listed but never decide a status.",
    f"Freshness: an observation older than {FRESHNESS_HOURS}h at as-of, or older than the latest accepted "
    "submission, cannot confirm a pass or a fail.",
    "Failed refresh (`refresh_status=failed`): the last good observation is kept as evidence and marked stale; "
    "never RESOLVED.",
    f"Processing window: {PROCESSING_WINDOW_HOURS}h after `accepted_at`. An observation at exactly "
    f"accepted_at + {PROCESSING_WINDOW_HOURS}h is outside the window (inclusive `>=`, a judgment call).",
    "`approved.csv` is a history: per key the newest `approved_at` is current; older values are SUPERSEDED.",
    "Policy: this tool only detects, verifies and prepares evidence. It changes no listings, contacts no one, "
    "makes no network calls and writes only to its output folder. Support messages are drafts for a human.",
]

POSSIBLE_CAUSES = {
    "ACCEPTED_NOT_APPLIED": [
        "contribution conflict: another contributor's value may be taking precedence",
        "schema change: the attribute may be read or stored differently than submitted",
        "processing delay longer than the assumed window",
    ],
    "MISMATCH": [
        "contribution conflict: another contributor's value may be taking precedence",
        "schema change: the attribute may be read or stored differently than expected",
    ],
    "UNKNOWN_NEEDS_REFRESH": ["missing observation: no fresh snapshot to compare against"],
    "UNKNOWN_OBSERVATION": ["missing observation: the snapshot returned no value for this attribute"],
    "PENDING_IN_WINDOW": [
        "processing delay: the accepted submission may still be applying",
        "missing observation: no snapshot taken since acceptance",
    ],
}


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _cell(value):
    return "" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def _pt(as_of):
    if as_of is None:
        return "PT unavailable"
    try:
        from zoneinfo import ZoneInfo

        return as_of.astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M %Z")
    except Exception:
        return "PT unavailable"


def _history_text(row):
    parts = []
    for h in row["observation_history"]:
        value = h["observed_value_raw"] or "(empty)"
        when = f"@ {h['observed_at']}" if h["timed"] else "(untimed)"
        flag = " [refresh failed]" if h["refresh_status"] == "failed" else ""
        parts.append(f"{value} {when}{flag}")
    return "; ".join(parts)


def _as_of_text(as_of):
    if as_of is None:
        return "unknown (no --as-of given and no observed_at in the observations)"
    return f"{fmt_ts(as_of)} ({_pt(as_of)}, display only)"


def report_md(rows, as_of, input_names, warnings=()):
    lines = [
        "# Catalog exceptions report",
        "",
        f"As of: {_as_of_text(as_of)}. All times UTC.",
        "",
        f"Inputs (verbatim copies in `raw/`): {', '.join(input_names)}",
        "",
        *(["## Warnings", "", *[f"- {w}" for w in warnings], ""] if warnings else []),
        "## Assumptions",
        "",
        *[f"- {a}" for a in ASSUMPTIONS],
        "",
        "## Exceptions (priority order)",
        "",
        "| # | Status | Seller | Marketplace | SKU | Attribute | Approved (raw) | Observed (raw) | Observed at "
        "| Reason | Next check | Who acts | Incident | Observation history |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        observed_at = r["observed_at"] or ""
        if r["observation_stale"]:
            observed_at += " (stale)"
        cells = [
            r["rank"], r["status"], r["seller_id"], r["marketplace_id"], r["sku"], r["attribute"],
            r["approved_value_raw"], r["observed_value_raw"], observed_at, r["reason"], r["next_check"],
            r["who_acts"], r["incident_id"], _history_text(r),
        ]
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return "\n".join(lines) + "\n"


def _facts(r):
    facts = [
        f"Approved value: {r['approved_value_raw']!r} (source {r['approved_source']}, approved_at {r['approved_at']}).",
    ]
    if r["observed_value_raw"] is not None:
        facts.append(
            f"Last good observation: {r['observed_value_raw']!r} at {r['observed_at']} "
            f"(snapshot {r['snapshot_id']}, source {r['observation_source']})."
        )
    else:
        facts.append("No timed observation with a value in the inputs.")
    for h in r["observation_history"]:
        if not h["timed"]:
            facts.append(f"Untimed observation {h['observed_value_raw']!r} (source {h['source']}); it does not decide status.")
    for t in r["failed_refreshes"]:
        facts.append(f"Refresh failed at {t or 'an untimed snapshot'}.")
    for s in r["submission_history"]:
        facts.append(f"Submission {s['submission_id']}: {s['submitted_value_raw']!r}, {s['status']} at {s['status_at'] or 'an unknown time (no status_at)'}.")
    if not r["submission_history"]:
        facts.append("No submissions for this key in the inputs.")
    return facts


def _next_step(r):
    if r["status"] == "MISMATCH":
        return "human review: confirm approved value, prepare correction for human approval"
    if r["status"] == "ACCEPTED_NOT_APPLIED":
        return ("human review: confirm approved value, prepare correction for human approval; "
                "a human decides whether to send the support draft below")
    if r["status"] == "PENDING_IN_WINDOW":
        return f"needs more data: re-check after {r['next_check']}, then rerun"
    return "needs more data: refresh the listing observation, then rerun"


def _draft(r):
    subject = f"SKU {r['sku']}, attribute `{r['attribute']}`, seller {r['seller_id']}, marketplace {r['marketplace_id']}"
    if r["status"] in HUMAN_REVIEW:
        opening = f"For {subject}, the listing shows a value that differs from our approved value."
    else:
        opening = f"For {subject}, we could not yet confirm the value shown on the listing."
    lines = ["Hello,", "", opening, "", f"- Approved value: \"{r['approved_value_raw']}\""]
    if r["observed_value_raw"] is not None:
        lines.append(f"- Value seen on the listing: \"{r['observed_value_raw']}\" (observed {r['observed_at']})")
    else:
        lines.append("- Value seen on the listing: no timed value recorded")
    if r["submission_history"]:
        lines.append("- Submission history: see attached evidence packet")
    if r["status"] in HUMAN_REVIEW:
        question = "Could you help us understand why the listing shows this value and what is needed for the approved value to appear?"
    else:
        question = "Could you help us confirm the value currently shown on the listing for this attribute?"
    lines += [
        "",
        question,
        "",
        "Thank you,",
        "[name]",
    ]
    return lines


def packet_md(r, as_of):
    verdict = "needs human review" if r["status"] in HUMAN_REVIEW else "needs more data"
    lines = [
        f"# Evidence packet {r['incident_id']}",
        "",
        f"**{r['status']}**: {verdict}",
        "",
        "| Field | Value |",
        "|---|---|",
        *[
            f"| {label} | {_cell(value)} |"
            for label, value in [
                ("Incident id", r["incident_id"]), ("Seller", r["seller_id"]), ("Marketplace", r["marketplace_id"]),
                ("SKU", r["sku"]), ("Attribute", r["attribute"]), ("As of", fmt_ts(as_of) or "unknown"),
                ("Reason", r["reason"]), ("Next check", r["next_check"]),
            ]
        ],
        "",
        "## Values",
        "",
        "| | Raw | Normalized | Source | Time |",
        "|---|---|---|---|---|",
        f"| Approved | {_cell(r['approved_value_raw'])} | {_cell(r['approved_value_normalized'])} "
        f"| {_cell(r['approved_source'])} | {_cell(r['approved_at'])} |",
        f"| Observed{' (stale)' if r['observation_stale'] else ''} | {_cell(r['observed_value_raw'])} "
        f"| {_cell(r['observed_value_normalized'])} | {_cell(r['observation_source'])} | {_cell(r['observed_at'])} |",
        "",
        "## Observation history (untimed rows first; they never decide status)",
        "",
        "| Snapshot | Value (raw) | Observed at | Source | Refresh |",
        "|---|---|---|---|---|",
        *([
            f"| {_cell(h['snapshot_id'])} | {_cell(h['observed_value_raw'])} | {_cell(h['observed_at'] or 'untimed')} "
            f"| {_cell(h['source'])} | {_cell(h['refresh_status'])} |"
            for h in r["observation_history"]
        ] or ["| (none) | | | | |"]),
        "",
        "## Submission history",
        "",
        "| Submission | Value (raw) | Status | Status at | Source |",
        "|---|---|---|---|---|",
        *([
            f"| {_cell(s['submission_id'])} | {_cell(s['submitted_value_raw'])} | {_cell(s['status'])} "
            f"| {_cell(s['status_at'] or 'untimed')} | {_cell(s['source'])} |"
            for s in r["submission_history"]
        ] or ["| (none) | | | | |"]),
        "",
        "## Facts (from the inputs)",
        "",
        *[f"- {f}" for f in _facts(r)],
        "",
        "## Possible causes (hypotheses, not verified)",
        "",
        *[f"- Hypothesis: {c}" for c in POSSIBLE_CAUSES[r["status"]]],
        "",
        "## Suggested next step (human approval needed)",
        "",
        f"- {_next_step(r)}",
        *([] if r["status"] in HUMAN_REVIEW else ["- Hold the draft below until more data is in."]),
        "- This tool changes no listings and contacts no one.",
        "",
        f"## Support message: {DRAFT_MARK}",
        "",
        *_draft(r),
    ]
    return "\n".join(lines) + "\n"


def prepare_out(out):
    """Refuse a non-empty folder fltrial did not create; in its own folder clear only packets/ and raw/."""
    if out.exists() and not out.is_dir():
        raise OutDirError(f"--out {out} exists and is not a directory")
    if out.exists() and any(out.iterdir()) and not (out / OUT_MARKER).is_file():
        raise OutDirError(f"refusing --out {out}: it is not empty and was not created by fltrial (no {OUT_MARKER} marker)")
    out.mkdir(parents=True, exist_ok=True)
    _write(out / OUT_MARKER, OUT_MARKER_TEXT)
    for sub in ("packets", "raw"):
        shutil.rmtree(out / sub, ignore_errors=True)


def write_outputs(out, rows, as_of, input_paths, warnings=()):
    out = Path(out)
    prepare_out(out)
    warnings = list(warnings) + [
        f"{r['seller_id']}/{r['marketplace_id']}/{r['sku']}/{r['attribute']}: {w}" for r in rows for w in r["warnings"]
    ]
    (out / "packets").mkdir(parents=True)
    load.copy_raw(input_paths, out / "raw")
    input_names = [Path(p).name for p in input_paths]
    for r in rows:
        if r["packet"]:
            _write(out / r["packet"], packet_md(r, as_of))
    report = {
        "as_of": fmt_ts(as_of),
        "freshness_hours": FRESHNESS_HOURS,
        "processing_window_hours": PROCESSING_WINDOW_HOURS,
        "inputs": input_names,
        "warnings": warnings,
        "rows": rows,
    }
    _write(out / "report.json", json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write(out / "report.md", report_md(rows, as_of, input_names, warnings))
