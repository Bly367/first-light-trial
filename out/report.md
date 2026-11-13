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
| 1 | ACCEPTED_NOT_APPLIED | DEMO1 | US | DEMO-002 | pack_count | 2 | 1 | 2026-10-26T09:00:00Z | We compared the approved value "2" with the listing value "1" seen at 2026-10-26T09:00:00Z. It is not still pending, because the listing was checked 24 hours or more after sub-002-1 was accepted at 2026-10-25T09:00:00Z, and it is not verified as fixed, because the listing still shows a different value. It is ranked first, for human review, because an accepted fix that did not show up on the listing is the most urgent kind of problem. | refresh after human correction | human review, top priority | f81e12c7d9ab | 1 @ 2026-10-26T09:00:00Z |
| 2 | MISMATCH | DEMO1 | US | DEMO-001 | color | Navy | Blue | 2026-10-26T09:00:00Z | We compared the approved value "Navy" with the listing value "Blue" seen at 2026-10-26T09:00:00Z. This is not a match or a formatting-only difference, because the values really differ, and it is not an accepted fix that did not apply, because there is no accepted submission with a recorded time. It is ranked after accepted fixes that did not apply: a confirmed mismatch needs a human, but nothing already submitted has failed to show up. | refresh after human correction | human review | a89c7bd5fe8d | Blue @ 2026-10-26T09:00:00Z |
| 3 | UNKNOWN_OBSERVATION | DEMO1 | US | DEMO-004 | item_name | Studio Bowl |  |  | The approved value is "Studio Bowl", but there is no usable listing value to compare it with: no snapshot has both a real value and a time. It is not a mismatch, because we never saw a real listing value. It is ranked below confirmed problems; the next step is to get a listing snapshot first. | refresh | needs more data | d9c1a9ec5e12 | UNKNOWN (untimed) |
| 4 | PENDING_IN_WINDOW | DEMO1 | US | DEMO-006 | size | Large | Medium | 2026-10-23T09:00:00Z (stale) | We compared the approved value "Large" with the listing value "Medium" seen at 2026-10-23T09:00:00Z. It is not treated as an accepted fix that did not apply, because sub-006-1 was accepted at 2026-10-26T08:55:00Z, its 24-hour window is still open, and the listing has not been checked since then, so it is too early to call it a problem. It is ranked lower because the next step is to wait until 2026-10-27T08:55:00Z and check again. | 2026-10-27T08:55:00Z | needs more data | e6cc4203200a | Medium @ 2026-10-23T09:00:00Z |
| 5 | MATCH_FORMAT_ONLY | DEMO1 | US | DEMO-003 | material | Cotton | cotton | 2026-10-26T09:00:00Z | We compared the approved value "Cotton" with the listing value "cotton" seen at 2026-10-26T09:00:00Z. It is not a mismatch, because the values are the same once formatting such as case and spacing is ignored. It is listed for information only, ranked below every open problem, and has no evidence packet. | none (info) | none, listed as info | 00be21e41273 | cotton @ 2026-10-26T09:00:00Z |
| 6 | RESOLVED_VERIFIED | DEMO1 | US | DEMO-005 | color | Cream | Cream | 2026-10-26T09:00:00Z | We compared the approved value "Cream" with the listing value "Cream" seen at 2026-10-26T09:00:00Z. It is not pending or unapplied, because this listing value was seen after sub-005-1 was accepted at 2026-10-25T09:00:00Z and it matches the approved value. It is ranked last among active rows; no action is needed. | none | none | cf947aa276f9 | Gold (untimed); Cream @ 2026-10-26T09:00:00Z |
