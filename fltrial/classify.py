"""Status rules, freshness, processing window, priority and incident ids (SPEC §3-§4)."""
import hashlib
from datetime import datetime, timedelta, timezone

from .normalize import is_no_observation, normalize

FRESHNESS_HOURS = 72
PROCESSING_WINDOW_HOURS = 24

PRIORITY = {
    "ACCEPTED_NOT_APPLIED": 0,
    "MISMATCH": 1,
    "UNKNOWN_NEEDS_REFRESH": 2,
    "UNKNOWN_OBSERVATION": 3,
    "PENDING_IN_WINDOW": 4,
    "MATCH_FORMAT_ONLY": 5,
    "RESOLVED_VERIFIED": 6,
    "MATCH": 6,
    "SUPERSEDED": 7,
}
NO_PACKET = {"MATCH", "MATCH_FORMAT_ONLY", "RESOLVED_VERIFIED", "SUPERSEDED"}
HUMAN_REVIEW = {"ACCEPTED_NOT_APPLIED", "MISMATCH"}
WHO_ACTS = {
    "ACCEPTED_NOT_APPLIED": "human review, top priority",
    "MISMATCH": "human review",
    "UNKNOWN_NEEDS_REFRESH": "needs more data",
    "UNKNOWN_OBSERVATION": "needs more data",
    "PENDING_IN_WINDOW": "needs more data",
    "MATCH_FORMAT_ONLY": "none, listed as info",
}
KEY_FIELDS = ("seller_id", "marketplace_id", "sku", "attribute")


def parse_ts(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def fmt_ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def key_of(row):
    return tuple(row[f] for f in KEY_FIELDS)


def incident_id(key, approved):
    normalized = normalize(approved["approved_value_raw"], approved["value_type"])
    return hashlib.sha1("|".join(key + (normalized,)).encode("utf-8")).hexdigest()[:12]


def compare(approved_raw, observed_raw, value_type):
    if approved_raw == observed_raw:
        return "MATCH"
    if normalize(approved_raw, value_type) == normalize(observed_raw, value_type):
        return "MATCH_FORMAT_ONLY"
    return "MISMATCH"


def _group(rows):
    grouped = {}
    for row in rows:
        grouped.setdefault(key_of(row), []).append(row)
    return grouped


def classify_all(approved, observations, submissions, as_of):
    obs_by_key = _group(observations)
    subs_by_key = _group(submissions)
    rows = []
    for key, versions in _group(approved).items():
        versions = sorted(versions, key=lambda a: parse_ts(a["approved_at"]))
        current = versions[-1]
        rows.append(classify_key(key, current, obs_by_key.get(key, []), subs_by_key.get(key, []), as_of))
        seen = {rows[-1]["incident_id"]}
        for old in reversed(versions[:-1]):
            if incident_id(key, old) not in seen:
                seen.add(incident_id(key, old))
                rows.append(_superseded(key, old, current))
    rows.sort(key=lambda r: (PRIORITY[r["status"]],) + key_of(r))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def _base_row(key, approved):
    iid = incident_id(key, approved)
    return {
        "rank": None,
        "incident_id": iid,
        **dict(zip(KEY_FIELDS, key)),
        "status": None,
        "who_acts": None,
        "reason": None,
        "next_check": None,
        "approved_value_raw": approved["approved_value_raw"],
        "approved_value_normalized": normalize(approved["approved_value_raw"], approved["value_type"]),
        "value_type": approved["value_type"],
        "approved_source": approved["source"],
        "approved_at": approved["approved_at"],
        "observed_value_raw": None,
        "observed_value_normalized": None,
        "observed_at": None,
        "observation_source": None,
        "snapshot_id": None,
        "observation_stale": False,
        "failed_refreshes": [],
        "observation_history": [],
        "submission_history": [],
        "packet": None,
        "warnings": [],
    }


def _superseded(key, old, current):
    row = _base_row(key, old)
    row.update(
        status="SUPERSEDED",
        who_acts="none",
        reason=f"approved value replaced by {current['approved_value_raw']!r} (approved_at {current['approved_at']})",
        next_check="none",
    )
    return row


def classify_key(key, approved, observations, submissions, as_of):
    row = _base_row(key, approved)
    visible = [o for o in observations if not o["observed_at"] or as_of is None or parse_ts(o["observed_at"]) <= as_of]
    untimed_subs = [s for s in submissions if not s["status_at"]]
    timed_subs = sorted(
        (s for s in submissions if s["status_at"] and (as_of is None or parse_ts(s["status_at"]) <= as_of)),
        key=lambda s: parse_ts(s["status_at"]),
    )
    subs = untimed_subs + timed_subs
    untimed = [o for o in visible if not o["observed_at"]]
    timed = sorted((o for o in visible if o["observed_at"]), key=lambda o: parse_ts(o["observed_at"]))
    row["observation_history"] = [
        {
            "snapshot_id": o["snapshot_id"] or None,
            "observed_value_raw": o["observed_value_raw"],
            "observed_at": o["observed_at"] or None,
            "timed": bool(o["observed_at"]),
            "source": o["source"],
            "refresh_status": o["refresh_status"],
        }
        for o in untimed + timed
    ]
    row["submission_history"] = [
        {**{f: s[f] for f in ("submission_id", "submitted_value_raw", "status", "source")}, "status_at": s["status_at"] or None}
        for s in subs
    ]
    untimed_accepted = [s for s in untimed_subs if s["status"] == "accepted"]
    untimed_other = [s for s in untimed_subs if s["status"] != "accepted"]
    untimed_note = "".join(
        f"; {s['submission_id']} ({s['status']}) has no status_at, so it does not decide status" for s in untimed_subs
    )
    row["warnings"] = [
        f"submission {s['submission_id']} was accepted but has no status_at: the acceptance time is unknown, "
        "so the processing window can't be judged"
        for s in untimed_accepted
    ] + [
        f"submission {s['submission_id']} has no status_at; listed as untimed and does not decide status"
        for s in untimed_other
    ]

    good = [o for o in timed if o["refresh_status"] != "failed" and not is_no_observation(o["observed_value_raw"])]
    last = good[-1] if good else None
    last_t = parse_ts(last["observed_at"]) if last else None
    failed = [
        o for o in visible
        if o["refresh_status"] == "failed" and o["observed_at"] and (last_t is None or parse_ts(o["observed_at"]) > last_t)
    ]
    accepted = [s for s in timed_subs if s["status"] == "accepted"]
    acc = accepted[-1] if accepted else None
    acc_t = parse_ts(acc["status_at"]) if acc else None

    too_old = last is not None and as_of is not None and as_of - last_t > timedelta(hours=FRESHNESS_HOURS)
    before_acc = last is not None and acc is not None and last_t < acc_t
    if last:
        row.update(
            observed_value_raw=last["observed_value_raw"],
            observed_value_normalized=normalize(last["observed_value_raw"], approved["value_type"]),
            observed_at=last["observed_at"],
            observation_source=last["source"],
            snapshot_id=last["snapshot_id"] or None,
            observation_stale=bool(too_old or before_acc or failed),
        )
    row["failed_refreshes"] = [o["observed_at"] or None for o in failed]
    result = compare(approved["approved_value_raw"], last["observed_value_raw"], approved["value_type"]) if last else None
    seen = f"observed {last['observed_value_raw']!r} at {last['observed_at']}" if last else ""

    if acc:
        window_end = acc_t + timedelta(hours=PROCESSING_WINDOW_HOURS)
        accepted_txt = f"{acc['submission_id']} accepted at {acc['status_at']}"
        if last is None or before_acc or too_old:
            if as_of is None:
                status, next_check = "UNKNOWN_NEEDS_REFRESH", "refresh"
                reason = (f"{accepted_txt}; as-of unknown, so the processing window (ends {fmt_ts(window_end)}) "
                          "cannot be checked; no timed observation")
            elif as_of < window_end:
                status, next_check = "PENDING_IN_WINDOW", fmt_ts(window_end)
                reason = f"{accepted_txt}; no observation since acceptance; inside the {PROCESSING_WINDOW_HOURS}h processing window"
            else:
                status, next_check = "UNKNOWN_NEEDS_REFRESH", "refresh"
                reason = f"{accepted_txt}; processing window ended {fmt_ts(window_end)}; no fresh observation since acceptance"
        elif result != "MISMATCH":
            if failed:
                status, next_check = "UNKNOWN_NEEDS_REFRESH", "refresh"
                reason = f"{accepted_txt}; {seen} matches, but a newer refresh failed, so it cannot be confirmed"
            else:
                status, next_check = "RESOLVED_VERIFIED", "none"
                reason = f"{accepted_txt}; {seen} matches the approved value"
        elif last_t >= window_end:
            status, next_check = "ACCEPTED_NOT_APPLIED", "refresh after human correction"
            reason = f"{accepted_txt}; {seen}, at or after the window end {fmt_ts(window_end)}, still differs"
        else:
            status, next_check = "PENDING_IN_WINDOW", fmt_ts(window_end)
            reason = f"{accepted_txt}; {seen} still differs but is inside the processing window"
    elif last is None:
        status, next_check = "UNKNOWN_OBSERVATION", "refresh"
        reason = "no timed observation with a value (UNKNOWN, empty or untimed rows only)"
    elif too_old:
        status, next_check = "UNKNOWN_NEEDS_REFRESH", "refresh"
        reason = f"last good observation at {last['observed_at']} is older than {FRESHNESS_HOURS}h"
    else:
        status = result
        next_check = {"MISMATCH": "refresh after human correction", "MATCH_FORMAT_ONLY": "none (info)"}.get(status, "none")
        reason = {
            "MISMATCH": f"{seen} differs from the approved value; no timed accepted submission",
            "MATCH_FORMAT_ONLY": f"{seen} matches after normalization; raw values differ",
            "MATCH": f"{seen} matches exactly",
        }[status]
    reason += untimed_note
    if failed and last:
        reason += f"; observation marked stale: newer refresh failed ({', '.join(o['observed_at'] or 'untimed' for o in failed)})"

    row.update(status=status, reason=reason, next_check=next_check, who_acts=WHO_ACTS.get(status, "none"))
    if status not in NO_PACKET:
        row["packet"] = f"packets/{row['incident_id']}.md"
    return row
