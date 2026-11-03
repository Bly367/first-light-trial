# first-light-trial
First Light Studios trial: Amazon catalog exceptions prototype

A Python 3 standard-library CLI that compares an approved product dataset with mock listing snapshots and
submission history, then writes a prioritized exception report and one evidence packet per unresolved incident.
See `docs/SPEC.md` for the full rules.

## Run

```bash
python3 -m fltrial run --as-of 2026-10-26T12:00:00Z
```

Defaults: `--approved fixtures/approved.csv --observations fixtures/observations.csv
--submissions fixtures/submissions.csv --out out`. Without `--as-of`, the newest `observed_at` in the
observations is used. Outputs:

- `out/report.md`, `out/report.json`: one row per (seller, marketplace, SKU, attribute) with status, reason and next check
- `out/packets/<incident_id>.md`: evidence packet with a human-only support draft, for unresolved incidents
- `out/raw/`: verbatim copies of the inputs

Variants for live review live in `fixtures/variants/` (`changed_value`, `second_marketplace`, `failed_refresh`).
Point the matching flag at a variant file, e.g.
`python3 -m fltrial run --approved fixtures/variants/changed_value/approved.csv --as-of 2026-10-26T12:00:00Z`.
Reruns on the same inputs and `--as-of` produce byte-identical outputs.

`--out` must be a new or empty folder, or one fltrial created earlier (it writes a `.fltrial-out` marker there).
A non-empty folder without the marker is refused. In its own folder fltrial clears only `packets/` and `raw/`
and rewrites the report files; anything else you put there is left alone. If times are missing (no `--as-of`
and no `observed_at`, or a blank `status_at`), the run still completes and lists the gaps under Warnings.

## Tests

```bash
python3 -m pip install pytest
python3 -m pytest
```

## Assumptions

Printed at the top of `out/report.md`: comparison-only normalization (whitespace, NFKC, casefold, numeric `int`),
no synonyms, `UNKNOWN`/empty/`None` means no observation, untimed rows never decide status, 72h freshness,
24h processing window with an inclusive `>=` boundary, and `approved.csv` as a history (newest `approved_at` wins).

## Policy boundary

Mock data only. The tool makes no network calls, changes no listings, and never opens, sends or replies to a
support case. It writes only to its output folder. Every packet's support message is a draft for a human to
review and send.
