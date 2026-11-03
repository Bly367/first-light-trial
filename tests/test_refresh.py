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
