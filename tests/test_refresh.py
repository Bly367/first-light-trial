from conftest import FIXTURES, TS_RE, rewrite_csv


def test_t8_failed_refresh(run):
    # (a) newer failed refresh row for DEMO-001, at the fixture as-of
    a = run(variant="failed_refresh")
    row = a.row("DEMO-001")
    assert row["status"] == "MISMATCH"
    assert row["observation_stale"] is True
    assert row["observed_value_raw"] == "Blue"
    assert row["observed_at"] == "2026-10-26T09:00:00Z"
    assert "stale" in a.packet(row).lower()
    assert a.row("DEMO-004")["status"] == "UNKNOWN_OBSERVATION"
    assert a.row("DEMO-005")["status"] == "RESOLVED_VERIFIED"

    # (b) same inputs, as-of more than 72h after the last good observation
    b = run(variant="failed_refresh", as_of="2026-10-29T12:00:00Z", out_name="out_b")
    row = b.row("DEMO-001")
    assert row["status"] == "UNKNOWN_NEEDS_REFRESH"
    assert row["next_check"] == "refresh"
    assert row["observed_value_raw"] == "Blue"
    assert row["observation_stale"] is True
    assert b.row("DEMO-004")["status"] == "UNKNOWN_OBSERVATION"
    assert all(r["status"] != "RESOLVED_VERIFIED" for r in b.rows)


def test_untimed_failed_row_never_decides_status(run, tmp_path):
    def add_untimed_failed(rows):
        extra = dict(rows[0], snapshot_id="", sku="DEMO-005", attribute="color",
                     observed_value_raw="", observed_at="", refresh_status="failed")
        return rows + [extra]

    obs = rewrite_csv(FIXTURES / "observations.csv", tmp_path / "observations.csv", add_untimed_failed)
    r = run(overrides={"observations": obs})
    row = r.row("DEMO-005")
    assert row["status"] == "RESOLVED_VERIFIED"
    assert row["observation_stale"] is False
    assert row["failed_refreshes"] == []
    assert r.packet(row) is None
    assert any(h["refresh_status"] == "failed" and not h["timed"] for h in row["observation_history"])


def test_no_as_of_and_no_observed_at_reports_unknown(run, tmp_path):
    obs = rewrite_csv(
        FIXTURES / "observations.csv", tmp_path / "observations.csv",
        lambda rows: [dict(row, observed_at="") for row in rows],
    )
    r = run(overrides={"observations": obs}, as_of=None)
    assert r.data["as_of"] is None
    assert any("as-of" in w for w in r.data["warnings"])
    assert "As of: unknown" in r.md
    assert {row["sku"]: row["status"] for row in r.rows} == {
        "DEMO-001": "UNKNOWN_OBSERVATION",
        "DEMO-002": "UNKNOWN_NEEDS_REFRESH",
        "DEMO-003": "UNKNOWN_OBSERVATION",
        "DEMO-004": "UNKNOWN_OBSERVATION",
        "DEMO-005": "UNKNOWN_NEEDS_REFRESH",
        "DEMO-006": "UNKNOWN_NEEDS_REFRESH",
    }
    assert all(row["next_check"] == "refresh" for row in r.rows)
    assert "as-of unknown" in r.row("DEMO-002")["reason"]
    allowed = r.allowed_timestamps()
    for ts in TS_RE.findall(r.output_text()):
        assert ts in allowed, f"invented timestamp {ts}"


def _blank_status_at(tmp_path, sub_ids):
    return rewrite_csv(
        FIXTURES / "submissions.csv", tmp_path / "submissions.csv",
        lambda rows: [dict(row, status_at="") if row["submission_id"] in sub_ids else row for row in rows],
    )


def _has_untimed_acceptance_warning(r, sub_id):
    return any(
        sub_id in w and "acceptance time is unknown" in w and "processing window can't be judged" in w
        for w in r.data["warnings"]
    )


def test_t14a_untimed_acceptance_keeps_mismatch(run, tmp_path):
    r = run(overrides={"submissions": _blank_status_at(tmp_path, {"sub-002-1"})})
    row = r.row("DEMO-002")
    assert row["status"] == "MISMATCH"
    assert row["status"] != "UNKNOWN_NEEDS_REFRESH"
    assert row["observed_value_raw"] == "1"
    assert "sub-002-1" in row["reason"] and "no status_at" in row["reason"]
    assert row["submission_history"][0]["submission_id"] == "sub-002-1"
    assert row["submission_history"][0]["status_at"] is None
    assert _has_untimed_acceptance_warning(r, "sub-002-1")
    packet = r.packet(row)
    assert packet is not None
    assert "human review" in packet
    assert r.row("DEMO-001")["status"] == "MISMATCH"
    assert r.row("DEMO-006")["status"] == "PENDING_IN_WINDOW"


def test_t14b_untimed_acceptance_never_resolves_a_match(run, tmp_path):
    r = run(overrides={"submissions": _blank_status_at(tmp_path, {"sub-005-1"})})
    row = r.row("DEMO-005")
    assert row["status"] in {"MATCH", "MATCH_FORMAT_ONLY"}
    assert row["status"] not in {"RESOLVED_VERIFIED", "UNKNOWN_NEEDS_REFRESH"}
    assert row["observed_value_raw"] == "Cream"
    assert "sub-005-1" in row["reason"] and "no status_at" in row["reason"]
    assert _has_untimed_acceptance_warning(r, "sub-005-1")


def test_timed_acceptance_still_decides_beside_an_untimed_one(run, tmp_path):
    def add_untimed_copy(rows):
        timed = next(row for row in rows if row["submission_id"] == "sub-002-1")
        return rows + [dict(timed, submission_id="sub-002-2", status_at="")]

    subs = rewrite_csv(FIXTURES / "submissions.csv", tmp_path / "submissions.csv", add_untimed_copy)
    r = run(overrides={"submissions": subs})
    row = r.row("DEMO-002")
    assert row["status"] == "ACCEPTED_NOT_APPLIED"
    assert "sub-002-1 accepted at 2026-10-25T09:00:00Z" in row["reason"]
    assert _has_untimed_acceptance_warning(r, "sub-002-2")
