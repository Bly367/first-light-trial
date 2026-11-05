def _snapshot(out):
    return {
        p.relative_to(out).as_posix(): p.read_bytes()
        for p in sorted(out.rglob("*"))
        if p.is_file()
    }


def test_t7_idempotent_rerun(run):
    first = run()
    first_bytes = _snapshot(first.out)
    first_ids = [r["incident_id"] for r in first.rows]

    second = run()
    assert _snapshot(second.out) == first_bytes
    assert [r["incident_id"] for r in second.rows] == first_ids
    assert len(second.packet_files()) == 4


def test_t9_changed_approved_value_supersedes_old_incident(run):
    base = run()
    old_id = base.row("DEMO-001")["incident_id"]
    base_other_ids = {r["sku"]: r["incident_id"] for r in base.rows if r["sku"] != "DEMO-001"}

    changed = run(variant="changed_value")
    row = changed.row("DEMO-001")
    assert row["status"] == "MATCH"
    assert row["approved_value_raw"] == "Blue"
    assert row["incident_id"] != old_id
    assert changed.packet(row) is None

    superseded = [r for r in changed.rows if r["status"] == "SUPERSEDED"]
    assert [r["incident_id"] for r in superseded] == [old_id]
    assert superseded[0]["approved_value_raw"] == "Navy"
    assert changed.rows[-1]["incident_id"] == old_id
    assert not (changed.out / "packets" / f"{old_id}.md").exists()
    assert len(changed.packet_files()) == 3

    changed_other_ids = {r["sku"]: r["incident_id"] for r in changed.rows if r["sku"] != "DEMO-001"}
    assert changed_other_ids == base_other_ids
