# Evidence packet a89c7bd5fe8d

**MISMATCH**: needs human review

| Field | Value |
|---|---|
| Incident id | a89c7bd5fe8d |
| Seller | DEMO1 |
| Marketplace | US |
| SKU | DEMO-001 |
| Attribute | color |
| As of | 2026-10-26T12:00:00Z |
| Next check | refresh after human correction |

## Why this status

We compared the approved value "Navy" with the listing value "Blue" seen at 2026-10-26T09:00:00Z. This is not a match or a formatting-only difference, because the values really differ, and it is not an accepted fix that did not apply, because there is no accepted submission with a recorded time. It is ranked after accepted fixes that did not apply: a confirmed mismatch needs a human, but nothing already submitted has failed to show up.

## Values

| | Raw | Normalized | Source | Time |
|---|---|---|---|---|
| Approved | Navy | navy | brand_master_v1 | 2026-10-20T00:00:00Z |
| Observed | Blue | blue | mock_listing_snapshot | 2026-10-26T09:00:00Z |

## Observation history (untimed rows first; they never decide status)

| Snapshot | Value (raw) | Observed at | Source | Refresh |
|---|---|---|---|---|
| snap-2026-10-26-0900-US | Blue | 2026-10-26T09:00:00Z | mock_listing_snapshot | ok |

## Submission history

| Submission | Value (raw) | Status | Status at | Source |
|---|---|---|---|---|
| (none) | | | | |

## Facts (from the inputs)

- Approved value: 'Navy' (source brand_master_v1, approved_at 2026-10-20T00:00:00Z).
- Last good observation: 'Blue' at 2026-10-26T09:00:00Z (snapshot snap-2026-10-26-0900-US, source mock_listing_snapshot).
- No submissions for this key in the inputs.

## Possible causes (hypotheses, not verified)

- Hypothesis: contribution conflict: another contributor's value may be taking precedence
- Hypothesis: schema change: the attribute may be read or stored differently than expected

## Suggested next step (human approval needed)

- human review: confirm approved value, prepare correction for human approval
- Please attach the evidence packet before sending.
- This tool changes no listings and contacts no one.

## Support message: DRAFT — for a human to review and send

> Please attach the evidence packet before sending.

Hello,

For SKU DEMO-001, attribute `color`, seller DEMO1, marketplace US, the listing shows a value that differs from our approved value.

- Approved value: "Navy"
- Value seen on the listing: "Blue" (observed 2026-10-26T09:00:00Z)

Could you help us understand why the listing shows this value and what is needed for the approved value to appear?

Thank you,
[name]
