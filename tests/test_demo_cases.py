from conftest import TS_RE


def test_t1_demo001_mismatch_without_submission(run):
    r = run()
    row = r.row("DEMO-001")
    assert row["status"] == "MISMATCH"
    assert row["approved_value_raw"] == "Navy"
    assert row["observed_value_raw"] == "Blue"
    packet = r.packet(row)
    assert packet is not None
    assert "human review: confirm approved value, prepare correction for human approval" in packet


def test_t2_demo002_accepted_not_applied_ranks_first(run):
    r = run()
    row = r.row("DEMO-002")
    assert row["status"] == "ACCEPTED_NOT_APPLIED"
    assert row["rank"] == 1
    assert r.rows[0]["sku"] == "DEMO-002"
    packet = r.packet(row)
    assert packet is not None
    assert "sub-002-1" in packet
    assert "accepted" in packet
    assert "2026-10-25T09:00:00Z" in packet


def test_t3_demo003_format_only_match(run):
    r = run()
    row = r.row("DEMO-003")
    assert row["status"] == "MATCH_FORMAT_ONLY"
    assert r.packet(row) is None
    assert row["approved_value_raw"] == "Cotton"
    assert row["observed_value_raw"] == "cotton"
    md_lines = [line for line in r.md.splitlines() if "DEMO-003" in line]
    assert any("Cotton" in line and "cotton" in line for line in md_lines)


def test_t4_demo004_unknown_observation(run):
    r = run()
    row = r.row("DEMO-004")
    assert row["status"] == "UNKNOWN_OBSERVATION"
    assert row["next_check"] == "refresh"
    assert row["observed_at"] is None
    packet = r.packet(row)
    assert packet is not None
    assert "needs more data" in packet


def test_t5_demo005_resolved_on_timed_observation_only(run):
    r = run()
    row = r.row("DEMO-005")
    assert row["status"] == "RESOLVED_VERIFIED"
    assert row["observed_value_raw"] == "Cream"
    assert row["observed_at"] == "2026-10-26T09:00:00Z"
    assert r.packet(row) is None
    history = row["observation_history"]
    assert [h["observed_value_raw"] for h in history] == ["Gold", "Cream"]
    assert history[0]["observed_at"] is None
    assert history[0]["timed"] is False
    assert history[1]["observed_at"] == "2026-10-26T09:00:00Z"
    assert "Gold (untimed)" in r.md
    allowed = r.allowed_timestamps()
    for ts in TS_RE.findall(r.output_text()):
        assert ts in allowed, f"invented timestamp {ts}"


def test_t6_demo006_pending_in_window(run):
    r = run()
    row = r.row("DEMO-006")
    assert row["status"] == "PENDING_IN_WINDOW"
    assert row["next_check"] == "2026-10-27T08:55:00Z"
    packet = r.packet(row)
    assert packet is not None
    assert "needs more data" in packet
    assert "fail" not in row["reason"].lower()
    assert "fail" not in packet.lower()
