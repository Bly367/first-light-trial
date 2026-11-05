# Fixtures (MOCK data only)

Every value in these CSVs is invented mock data for the trial. None of the ids below refer to a real seller,
product, listing snapshot, submission or support case, and no file here came from an Amazon API or a browser.

| Id | Kind | Mock |
|---|---|---|
| DEMO1 | seller_id | MOCK |
| DEMO-001 | sku | MOCK |
| DEMO-002 | sku | MOCK |
| DEMO-003 | sku | MOCK |
| DEMO-004 | sku | MOCK |
| DEMO-005 | sku | MOCK |
| DEMO-006 | sku | MOCK |
| sub-002-1 | submission_id | MOCK |
| sub-005-1 | submission_id | MOCK |
| sub-006-1 | submission_id | MOCK |
| snap-2026-10-23-0900-US | snapshot_id | MOCK |
| snap-2026-10-26-0900-US | snapshot_id | MOCK |
| snap-2026-10-26-0900-CA | snapshot_id | MOCK (variant `second_marketplace`) |
| snap-2026-10-26-1200-US | snapshot_id | MOCK (variant `failed_refresh`) |

`marketplace_id` values (`US`, `CA`) are marketplace codes, used only as join keys.

Variants in `variants/` contain only the file they change; the other inputs come from this folder.
