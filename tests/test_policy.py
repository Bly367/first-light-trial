import re
import shutil
import socket

from conftest import AS_OF, DRAFT_MARK, FIXTURES, TS_RE, cli_args, input_paths

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
        draft = text.split(DRAFT_MARK, 1)[1]
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
