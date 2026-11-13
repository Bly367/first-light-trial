import re
import shutil
import socket

import pytest

from conftest import (
    AS_OF, ATTACH_REMINDER, DRAFT_MARK, FIXTURES, TS_RE, cli_args, input_paths, rewrite_csv, snapshot_tree,
)

CASE_NUMBER_RES = (
    re.compile(r"\bcase\s*(#|id\b|number|no\b)", re.I),
    re.compile(r"\bcase\s*:?\s*\d", re.I),
)
PRIOR_CONTACT_RE = re.compile(
    r"\b(already|previously)\s+(contacted|reached out|opened|raised|spoke)", re.I
)


def test_t11_no_network_and_writes_only_under_out(tmp_path, monkeypatch):
    work = tmp_path / "work"
    (work / "in").mkdir(parents=True)
    for name in ("approved", "observations", "submissions"):
        shutil.copyfile(FIXTURES / f"{name}.csv", work / "in" / f"{name}.csv")
    monkeypatch.chdir(work)

    def no_network(*args, **kwargs):
        raise AssertionError("network use attempted")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)

    before = {p: p.read_bytes() for p in work.rglob("*") if p.is_file()}
    from fltrial.__main__ import main

    paths = {name: f"in/{name}.csv" for name in ("approved", "observations", "submissions")}
    main(cli_args(paths, AS_OF, "out"))

    after = {p: p.read_bytes() for p in work.rglob("*") if p.is_file()}
    written = [p for p in after if before.get(p) != after[p]]
    assert written
    assert all(p.relative_to(work).parts[0] == "out" for p in written)
    assert all(after[p] == data for p, data in before.items())
    assert (work / "out" / "report.json").exists()


def test_t12_support_drafts_are_human_only(run):
    r = run()
    packets = r.packet_files()
    assert len(packets) == 4
    rows = {row["incident_id"]: row for row in r.rows}
    allowed = r.allowed_timestamps()
    for path in packets:
        text = path.read_text(encoding="utf-8")
        assert DRAFT_MARK in text
        evidence, draft = text.split(DRAFT_MARK, 1)
        assert ATTACH_REMINDER in draft, path.name
        if rows[path.stem]["status"] in {"MISMATCH", "ACCEPTED_NOT_APPLIED"}:
            next_step = evidence.split("## Suggested next step", 1)[1]
            assert "attach the evidence packet" in next_step, path.name
        for pattern in CASE_NUMBER_RES:
            assert not pattern.search(draft), path.name
        assert not PRIOR_CONTACT_RE.search(draft), path.name
        assert "we have already contacted" not in draft.lower()
        for ts in TS_RE.findall(draft):
            assert ts in allowed, f"{path.name}: timestamp {ts} not from inputs"
        row = rows[path.stem]
        assert row["sku"] in draft
        assert row["approved_value_raw"] in draft
        if row["observed_value_raw"]:
            assert row["observed_value_raw"] in draft


def test_t13_raw_copy_is_byte_identical(run):
    r = run()
    raw = r.out / "raw"
    assert sorted(p.name for p in raw.iterdir()) == sorted(p.name for p in input_paths().values())
    for path in input_paths().values():
        assert (raw / path.name).read_bytes() == path.read_bytes()


def test_support_draft_omits_submission_ids_and_values(run, tmp_path):
    marker = "MOCK-SUBMITTED-VALUE"
    subs = rewrite_csv(
        FIXTURES / "submissions.csv", tmp_path / "submissions.csv",
        lambda rows: [dict(row, submitted_value_raw=marker) for row in rows],
    )
    r = run(overrides={"submissions": subs})
    rows = {row["incident_id"]: row for row in r.rows}
    with_submissions = 0
    for path in r.packet_files():
        evidence, draft = path.read_text(encoding="utf-8").split(DRAFT_MARK, 1)
        row = rows[path.stem]
        assert marker not in draft, path.name
        assert not re.search(r"\bsub-\d", draft), path.name
        assert ATTACH_REMINDER in draft, path.name
        if row["submission_history"]:
            with_submissions += 1
            assert "see attached evidence packet" in draft
            assert marker in evidence
            for sub in row["submission_history"]:
                assert sub["submission_id"] in evidence
    assert with_submissions == 2


def test_out_refuses_non_empty_dir_it_did_not_create(tmp_path):
    from fltrial.__main__ import main

    foreign = tmp_path / "foreign"
    (foreign / "raw").mkdir(parents=True)
    (foreign / "keep.txt").write_text("mine", encoding="utf-8")
    (foreign / "raw" / "mine.csv").write_text("x", encoding="utf-8")
    before = snapshot_tree(foreign)
    with pytest.raises(SystemExit) as exc:
        main(cli_args(input_paths(), AS_OF, foreign))
    assert exc.value.code != 0
    assert snapshot_tree(foreign) == before

    empty = tmp_path / "empty"
    empty.mkdir()
    main(cli_args(input_paths(), AS_OF, empty))
    assert (empty / "report.json").exists()


def test_out_rerun_clears_only_tool_created_dirs(run):
    first = run()
    (first.out / "notes.txt").write_text("keep", encoding="utf-8")
    (first.out / "mine").mkdir()
    (first.out / "mine" / "x.txt").write_text("keep", encoding="utf-8")
    old_packet = first.out / "packets" / "000000000000.md"
    old_packet.write_text("old", encoding="utf-8")

    second = run()
    assert (second.out / "notes.txt").read_text(encoding="utf-8") == "keep"
    assert (second.out / "mine" / "x.txt").read_text(encoding="utf-8") == "keep"
    assert not old_packet.exists()
    assert len(second.packet_files()) == 4
