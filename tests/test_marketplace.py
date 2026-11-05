def test_t10_second_marketplace_never_merged(run):
    base = run(out_name="base")
    r = run(variant="second_marketplace")
    us = r.row("DEMO-001", "US")
    ca = r.row("DEMO-001", "CA")
    assert us["status"] == "MISMATCH"
    assert us["observed_value_raw"] == "Blue"
    assert ca["status"] == "MATCH"
    assert ca["observed_value_raw"] == "Navy"
    assert us["incident_id"] != ca["incident_id"]
    assert us["incident_id"] == base.row("DEMO-001", "US")["incident_id"]
    assert r.packet(us) is not None
    assert r.packet(ca) is None
