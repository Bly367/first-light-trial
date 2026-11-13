import re

from conftest import DRAFT_MARK, FIXTURES, rewrite_csv

JARGON = ("window end", "at or after", "still differs")
HYPOTHESES = ("contribution conflict", "schema change", "processing delay")


def _sentences(reason):
    return [s for s in re.split(r"(?<=\.)\s+", reason) if s]


def _check_plain(reason):
    low = reason.lower()
    for phrase in JARGON + HYPOTHESES:
        assert phrase not in low, phrase
    assert 2 <= len(_sentences(reason)) <= 3, reason


def test_t15_demo001_mismatch_reason(run):
    reason = run().row("DEMO-001")["reason"]
    _check_plain(reason)
    assert 'approved value "Navy"' in reason
    assert 'listing value "Blue" seen at 2026-10-26T09:00:00Z' in reason
    assert "not a match or a formatting-only difference, because the values really differ" in reason
    assert "not an accepted fix that did not apply, because there is no accepted submission with a recorded time" in reason
    assert "ranked after accepted fixes that did not apply" in reason
    assert "needs a human" in reason
    assert "nothing already submitted has failed to show up" in reason


def test_t15_demo002_accepted_not_applied_reason(run):
    reason = run().row("DEMO-002")["reason"]
    _check_plain(reason)
    assert 'approved value "2"' in reason
    assert 'listing value "1" seen at 2026-10-26T09:00:00Z' in reason
    assert "not still pending, because the listing was checked 24 hours or more after sub-002-1 was accepted at 2026-10-25T09:00:00Z" in reason
    assert "not verified as fixed, because the listing still shows a different value" in reason
    assert "ranked first" in reason
    assert "human review" in reason
    assert "most urgent" in reason


def test_t15_demo003_format_only_reason(run):
    reason = run().row("DEMO-003")["reason"]
    _check_plain(reason)
    assert 'approved value "Cotton"' in reason
    assert 'listing value "cotton" seen at 2026-10-26T09:00:00Z' in reason
    assert "not a mismatch, because the values are the same once formatting such as case and spacing is ignored" in reason
    assert "information only" in reason
    assert "ranked below every open problem" in reason
    assert "no evidence packet" in reason


def test_t15_demo004_unknown_observation_reason(run):
    reason = run().row("DEMO-004")["reason"]
    _check_plain(reason)
    assert 'approved value is "Studio Bowl"' in reason
    assert "no usable listing value" in reason
    assert "not a mismatch, because we never saw a real listing value" in reason
    assert "ranked below confirmed problems" in reason
    assert "get a listing snapshot first" in reason


def test_t15_demo005_resolved_reason(run):
    reason = run().row("DEMO-005")["reason"]
    _check_plain(reason)
    assert 'approved value "Cream"' in reason
    assert 'listing value "Cream" seen at 2026-10-26T09:00:00Z' in reason
    assert "Gold" not in reason
    assert "not pending or unapplied, because this listing value was seen after sub-005-1 was accepted at 2026-10-25T09:00:00Z and it matches the approved value" in reason
    assert "ranked last among active rows" in reason
    assert "no action is needed" in reason


def test_t15_demo006_pending_reason(run):
    reason = run().row("DEMO-006")["reason"]
    _check_plain(reason)
    assert "fail" not in reason.lower()
    assert 'approved value "Large"' in reason
    assert 'listing value "Medium" seen at 2026-10-23T09:00:00Z' in reason
    assert "not treated as an accepted fix that did not apply" in reason
    assert "sub-006-1 was accepted at 2026-10-26T08:55:00Z" in reason
    assert "24-hour window is still open" in reason
    assert "not been checked since then" in reason
    assert "too early to call it a problem" in reason
    assert "ranked lower because the next step is to wait until 2026-10-27T08:55:00Z and check again" in reason


def test_t15_packets_explain_status_once(run):
    r = run()
    packets = r.packet_files()
    assert len(packets) == 4
    rows = {row["incident_id"]: row for row in r.rows}
    for path in packets:
        text = path.read_text(encoding="utf-8")
        reason = rows[path.stem]["reason"]
        assert f"## Why this status\n\n{reason}\n" in text, path.name
        assert "| Reason |" not in text, path.name
        assert text.count(reason) == 1, path.name
        evidence, draft = text.split(DRAFT_MARK, 1)
        assert "Why this status" not in draft, path.name
        assert "ranked" not in draft.lower(), path.name
        for sentence in _sentences(reason):
            assert sentence not in draft, path.name


def test_t15_variant_reasons_follow_templates(run, tmp_path):
    a = run(variant="failed_refresh")
    reason = a.row("DEMO-001")["reason"]
    assert a.row("DEMO-001")["status"] == "MISMATCH"
    assert "not a match or a formatting-only difference, because the values really differ" in reason
    assert reason.endswith("The listing value is marked stale because a newer refresh failed (2026-10-26T12:00:00Z).")

    b = run(variant="failed_refresh", as_of="2026-10-29T12:00:00Z", out_name="out_b")
    reason = b.row("DEMO-001")["reason"]
    assert b.row("DEMO-001")["status"] == "UNKNOWN_NEEDS_REFRESH"
    assert 'listing value "Blue" seen at 2026-10-26T09:00:00Z' in reason
    assert "not a confirmed mismatch or a confirmed fix, because there is no fresh listing value" in reason
    assert "more than 72 hours old" in reason
    assert "next step is to get more data, not to escalate" in reason

    changed = run(variant="changed_value", out_name="out_changed")
    row = changed.row("DEMO-001")
    assert row["status"] == "MATCH"
    assert 'approved value "Blue"' in row["reason"] and "match exactly" in row["reason"]
    old = next(r for r in changed.rows if r["status"] == "SUPERSEDED")
    assert old["reason"].startswith('The approved value "Navy" was replaced by "Blue"')
    assert "sorts last" in old["reason"]

    ca = run(variant="second_marketplace", out_name="out_ca").row("DEMO-001", "CA")
    assert ca["status"] == "MATCH"
    assert 'listing value "Navy"' in ca["reason"] and "match exactly" in ca["reason"]

    subs = rewrite_csv(
        FIXTURES / "submissions.csv", tmp_path / "submissions.csv",
        lambda rows: [dict(row, status_at="") if row["submission_id"] == "sub-002-1" else row for row in rows],
    )
    row = run(overrides={"submissions": subs}, out_name="out_untimed").row("DEMO-002")
    assert row["status"] == "MISMATCH"
    assert "there is no accepted submission with a recorded time" in row["reason"]
    assert row["reason"].endswith(
        "Submission sub-002-1 (accepted) has no status_at, so its time is unknown and it does not decide the status."
    )
