import csv

from conftest import FIXTURES, ROOT

ID_FIELDS = ("seller_id", "sku", "submission_id", "snapshot_id")


def test_fixture_readme_marks_mock_ids():
    readme = FIXTURES / "README.md"
    assert readme.exists()
    lines = readme.read_text(encoding="utf-8").splitlines()
    ids = set()
    for path in FIXTURES.rglob("*.csv"):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ids.update(row[field] for field in ID_FIELDS if row.get(field))
    assert ids
    for mock_id in sorted(ids):
        assert any(mock_id in line and "MOCK" in line for line in lines), mock_id


def test_ci_workflow_runs_pytest():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    text = "\n".join(p.read_text(encoding="utf-8") for p in workflows)
    assert "actions/checkout" in text
    assert "pytest" in text
