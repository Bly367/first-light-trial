import csv
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
AS_OF = "2026-10-26T12:00:00Z"
INPUT_NAMES = ("approved", "observations", "submissions")
TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?Z")
DRAFT_MARK = "DRAFT — for a human to review and send"


def input_paths(variant=None):
    paths = {}
    for name in INPUT_NAMES:
        candidate = FIXTURES / "variants" / variant / f"{name}.csv" if variant else None
        paths[name] = candidate if candidate and candidate.exists() else FIXTURES / f"{name}.csv"
    return paths


def cli_args(paths, as_of, out):
    return [
        "run",
        "--approved", str(paths["approved"]),
        "--observations", str(paths["observations"]),
        "--submissions", str(paths["submissions"]),
        "--as-of", as_of,
        "--out", str(out),
    ]


def _parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


class Report:
    def __init__(self, out, inputs, as_of):
        self.out = Path(out)
        self.inputs = inputs
        self.as_of = as_of
        self.md = (self.out / "report.md").read_text(encoding="utf-8")
        self.data = json.loads((self.out / "report.json").read_text(encoding="utf-8"))
        self.rows = self.data["rows"]

    def row(self, sku, marketplace="US"):
        matches = [
            r for r in self.rows
            if r["sku"] == sku and r["marketplace_id"] == marketplace and r["status"] != "SUPERSEDED"
        ]
        assert len(matches) == 1, matches
        return matches[0]

    def packet(self, row):
        path = self.out / "packets" / f"{row['incident_id']}.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def packet_files(self):
        return sorted((self.out / "packets").glob("*.md"))

    def output_text(self):
        return "\n".join(
            p.read_text(encoding="utf-8")
            for p in sorted(self.out.rglob("*"))
            if p.is_file() and "raw" not in p.relative_to(self.out).parts
        )

    def allowed_timestamps(self):
        allowed = {self.as_of}
        for path in self.inputs.values():
            allowed.update(TS_RE.findall(path.read_text(encoding="utf-8")))
        with open(self.inputs["submissions"], newline="", encoding="utf-8") as f:
            for sub in csv.DictReader(f):
                if sub["status"] == "accepted":
                    end = _parse(sub["status_at"]) + timedelta(hours=24)
                    allowed.add(end.strftime("%Y-%m-%dT%H:%M:%SZ"))
        return allowed


@pytest.fixture
def run(tmp_path):
    def _run(variant=None, as_of=AS_OF, out_name="out"):
        from fltrial.__main__ import main

        paths = input_paths(variant)
        out = tmp_path / out_name
        main(cli_args(paths, as_of, out))
        return Report(out, paths, as_of)

    return _run
