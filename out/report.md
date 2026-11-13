# Catalog exceptions report

As of: 2026-10-26T12:00:00Z (2026-10-26 05:00 PDT, display only). All times UTC.

Inputs (verbatim copies in `raw/`): approved.csv, observations.csv, submissions.csv

## Assumptions

- Normalization is for comparison only: trim, collapse inner whitespace, Unicode NFKC, casefold; `int` attributes compare numerically (`2` == `2.0`). No synonym mapping. Raw values are always shown.
- `UNKNOWN`, empty, `None` or a missing row means no observation, never a mismatch. Rows without `observed_at`, and submissions without `status_at` (even accepted ones), are listed but never decide a status; an untimed acceptance adds a warning because the processing window can't be judged.
- Freshness: an observation older than 72h at as-of, or older than the latest accepted submission, cannot confirm a pass or a fail.
- Failed refresh (`refresh_status=failed`): the last good observation is kept as evidence and marked stale; never RESOLVED.
- Processing window: 24h after `accepted_at`. An observation at exactly accepted_at + 24h is outside the window (inclusive `>=`, a judgment call).
- `approved.csv` is a history: per key the newest `approved_at` is current; older values are SUPERSEDED.
- Policy: this tool only detects, verifies and prepares evidence. It changes no listings, contacts no one, makes no network calls and writes only to its output folder. Support messages are drafts for a human.

## Exceptions (priority order)

| # | Status | Seller | Marketplace | SKU | Attribute | Approved (raw) | Observed (raw) | Observed at | Reason | Next check | Who acts | Incident | Observation history |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | ACCEPTED_NOT_APPLIED | DEMO1 | US | DEMO-002 | pack_count | 2 | 1 | 2026-10-26T09:00:00Z | sub-002-1 accepted at 2026-10-25T09:00:00Z; observed '1' at 2026-10-26T09:00:00Z, at or after the window end 2026-10-26T09:00:00Z, still differs | refresh after human correction | human review, top priority | f81e12c7d9ab | 1 @ 2026-10-26T09:00:00Z |
| 2 | MISMATCH | DEMO1 | US | DEMO-001 | color | Navy | Blue | 2026-10-26T09:00:00Z | observed 'Blue' at 2026-10-26T09:00:00Z differs from the approved value; no timed accepted submission | refresh after human correction | human review | a89c7bd5fe8d | Blue @ 2026-10-26T09:00:00Z |
| 3 | UNKNOWN_OBSERVATION | DEMO1 | US | DEMO-004 | item_name | Studio Bowl |  |  | no timed observation with a value (UNKNOWN, empty or untimed rows only) | refresh | needs more data | d9c1a9ec5e12 | UNKNOWN (untimed) |
| 4 | PENDING_IN_WINDOW | DEMO1 | US | DEMO-006 | size | Large | Medium | 2026-10-23T09:00:00Z (stale) | sub-006-1 accepted at 2026-10-26T08:55:00Z; no observation since acceptance; inside the 24h processing window | 2026-10-27T08:55:00Z | needs more data | e6cc4203200a | Medium @ 2026-10-23T09:00:00Z |
| 5 | MATCH_FORMAT_ONLY | DEMO1 | US | DEMO-003 | material | Cotton | cotton | 2026-10-26T09:00:00Z | observed 'cotton' at 2026-10-26T09:00:00Z matches after normalization; raw values differ | none (info) | none, listed as info | 00be21e41273 | cotton @ 2026-10-26T09:00:00Z |
| 6 | RESOLVED_VERIFIED | DEMO1 | US | DEMO-005 | color | Cream | Cream | 2026-10-26T09:00:00Z | sub-005-1 accepted at 2026-10-25T09:00:00Z; observed 'Cream' at 2026-10-26T09:00:00Z matches the approved value | none | none | cf947aa276f9 | Gold (untimed); Cream @ 2026-10-26T09:00:00Z |
