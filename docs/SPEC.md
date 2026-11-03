# SPEC — First Light Studios trial: Amazon catalog exceptions prototype
Planner draft, Mon Nov 2, 2026 (PT). Planning only — no production code. Sources: Growth-AI-Practical-Trial-Project.pdf (brief), brian-agent-workflow-prd.md (PRD), first-light-handoff.md (handoff).

Hard rules (apply to every section):
- **Mock data only.** Fixtures are invented; no Amazon API calls, no browser bots, hidden endpoints, CAPTCHA workarounds, or shared credentials.
- **Support cases are human-only.** The tool writes a *draft* message for a human. It never opens, submits, sends, or replies to a case.
- **No automatic listing changes.** Anything about a listing is a *suggestion* that needs human approval. The tool makes no network calls and writes only to its own `out/` folder.

## 1. Outcome summary
A Python CLI that reads (a) an approved product dataset and (b) timestamped observed listing snapshots plus submission history. It writes:
- `out/report.md` + `out/report.json`: a prioritized exception report. Each row is one (seller, marketplace, SKU, attribute) with a status, a reason, and a next check.
- `out/packets/<incident_id>.md`: one evidence packet per unresolved incident. Each packet has ids, approved/observed values (raw + normalized), sources and timestamps, submission history, facts vs possible causes, a suggested next step (human approval needed), and a HUMAN support draft that invents no case history.
- `out/raw/`: a verbatim copy of the inputs.

Reruns are deterministic: the same inputs and the same `--as-of` give byte-identical outputs and the same incident ids. This also answers the brief's question: what we can automate safely is detection, verification, and evidence prep. Fixes and support contact stay with humans.

Expected statuses for the brief's fixtures (as-of 2026-10-26T12:00Z, rules in §3):
| SKU | Status | Who acts |
|---|---|---|
| DEMO-001 color Navy→Blue | MISMATCH (no submission) | human review |
| DEMO-002 pack_count 2→1 | ACCEPTED_NOT_APPLIED (window elapsed, still wrong) | human review, top priority |
| DEMO-003 material Cotton/cotton | MATCH_FORMAT_ONLY | none, listed as info |
| DEMO-004 item_name, UNKNOWN | UNKNOWN_OBSERVATION | needs more data |
| DEMO-005 color Cream (was Gold) | RESOLVED_VERIFIED | none |
| DEMO-006 size Large, last seen Medium before acceptance | PENDING_IN_WINDOW | needs more data, re-check after window |

## 2. Approaches compared
| | A. Python 3 stdlib CLI + pytest (**pick**) | B. Jupyter notebook (pandas) | C. No-code workflow (Sheets + Zapier/n8n) |
|---|---|---|---|
| Runnable / demo | `python -m fltrial run` is one command; easy to Loom | Good visuals, but hidden-state cell order makes reruns fragile | Visual, but hard to version and test |
| Idempotency / tests | Deterministic files; pytest | Hard to test | Hard to test; dedupe is manual |
| Dependencies | stdlib only (`csv`, `json`, `hashlib`, `datetime`) + pytest for dev | pandas, jupyter | SaaS accounts, credentials (a policy risk) |
| Live-review edits (change value, add marketplace) | Edit CSV, rerun | Edit, then re-run all cells | Edit sheet, re-trigger |
| Path to production | Swap the fixture loader for an authorized SP-API Listings read + notifications | Needs a rewrite | Lock-in |

**Pick A.** It's the simplest thing that runs, tests well, and has no deps or credentials. It matches the PRD/handoff default and the "subtract before add" practice. No strong reason to deviate.

## 3. Assumptions (documented in the one-pager and printed in the report header)
**Normalization** (only for comparing; the raw value is always kept and shown):
- Strip leading/trailing whitespace, collapse inner whitespace, Unicode NFKC, casefold. So `Cotton` == `cotton` → MATCH_FORMAT_ONLY, and the raw difference is still reported.
- Numeric attributes (`pack_count`): parse as int/decimal. `"2"` == `"2.0"`; `"2"` != `"1"`.
- No synonym mapping. `Navy` vs `Blue` is a mismatch, not "close enough". Synonyms are a human call.
- The sentinel values `UNKNOWN`, empty, `None`, or a missing row mean *no observation*, never a mismatch.

**Data freshness**:
- `--as-of` is required in tests and defaults to the newest snapshot time in demos. Fixtures use as-of `2026-10-26T12:00:00Z`. All times are UTC (as the brief says). The report header converts to PT only for display.
- An observation is **stale** if it is older than `freshness_hours = 72` at as-of, or older than the latest accepted submission for that key. An observation older than 72h at as-of can't confirm a pass or a fail: the status becomes UNKNOWN_NEEDS_REFRESH (or PENDING per the window rules) with a next check. Within 72h, a failed refresh doesn't erase the last good observation. Its status (e.g. MISMATCH) stands, flagged stale, and it still never becomes RESOLVED (see T8).
- **Failed refresh**: a snapshot row marked `refresh_status=failed`, or a key with no new timed observation. "Latest batch" means the newest timed `observed_at` per (seller_id, marketplace_id, sku, attribute); untimed rows never decide status. Treated as "no new observation". The last good observation is shown as evidence but marked stale. Never RESOLVED.

**Processing window**:
- `processing_window_hours = 24` after a submission's `accepted_at` (a configurable constant, stated in the report). Acceptance is intermediate, never resolution.
- After acceptance: no observation after `accepted_at` and still inside the window → PENDING_IN_WINDOW, next check = `accepted_at + 24h`. Outside the window with no fresh observation → UNKNOWN_NEEDS_REFRESH.
- An observation at or after `accepted_at + 24h` that matches → RESOLVED_VERIFIED. One that still mismatches → ACCEPTED_NOT_APPLIED.
- An observation after acceptance but inside the window that matches → RESOLVED_VERIFIED. One that mismatches → PENDING_IN_WINDOW (not a failure yet).
- Edge in the fixtures: DEMO-002 was observed exactly 24h after acceptance, which counts as out of window (inclusive `>=`). This is called out as a judgment call.

**Priority order** (report sort): ACCEPTED_NOT_APPLIED > MISMATCH > UNKNOWN_NEEDS_REFRESH > UNKNOWN_OBSERVATION > PENDING_IN_WINDOW > MATCH_FORMAT_ONLY > RESOLVED_VERIFIED / MATCH. Ties sort by seller, marketplace, SKU, attribute.

**Unresolved** = any status other than MATCH, MATCH_FORMAT_ONLY, RESOLVED_VERIFIED. Each unresolved key gets one packet. The packet says either "needs human review" (mismatch types) or "needs more data" (unknown/pending types).

## 4. Fixture schema (CSV, UTF-8, raw strings kept verbatim)
Join key everywhere: `seller_id, marketplace_id, sku, attribute`. Keys are never merged or casefolded across sellers or marketplaces.

`fixtures/approved.csv`
| column | example | notes |
|---|---|---|
| seller_id | DEMO1 | |
| marketplace_id | US | a second marketplace (e.g. `CA`) is just more rows |
| sku | DEMO-001 | |
| attribute | color | |
| approved_value_raw | Navy | stored as given |
| value_type | text \| int | drives normalization |
| source | brand_master_v1 | provenance |
| approved_at | 2026-10-20T00:00:00Z | |

`fixtures/observations.csv` (one row per snapshot per key, append-only history)
| column | example | notes |
|---|---|---|
| snapshot_id | snap-2026-10-26-0900-US | |
| seller_id, marketplace_id, sku, attribute | | key |
| observed_value_raw | Blue / UNKNOWN / empty | verbatim |
| observed_at | 2026-10-26T09:00:00Z | empty if never observed |
| source | mock_listing_snapshot | never a real endpoint |
| refresh_status | ok \| failed | `failed` → failed-refresh path |

`fixtures/submissions.csv`
| column | example |
|---|---|
| submission_id | sub-002-1 |
| seller_id, marketplace_id, sku, attribute | key |
| submitted_value_raw | 2 |
| status | accepted \| rejected \| submitted |
| status_at | 2026-10-25T09:00:00Z |
| source | mock_submission_log |

DEMO-005 is modeled as two observation rows: Gold with `observed_at` blank and source note `brief gives no time` (no time is invented; an untimed row can never resolve or fail a key), and Cream at 2026-10-26T09:00Z. Resolution rests only on the Cream observation after acceptance. DEMO-004 is one row with `UNKNOWN` and an empty `observed_at`. DEMO-006 has an observation at 2026-10-23T09:00Z (Medium) and an acceptance at 2026-10-26T08:55Z.

**Incident id** = `sha1(seller_id|marketplace_id|sku|attribute|normalized_approved_value)[:12]`. It's stable across reruns. A changed approved value creates a new id, and the old incident is listed as `SUPERSEDED` (no packet). `approved.csv` is a history: per key, the row with the newest `approved_at` is current; older rows are SUPERSEDED and sort last in the report. Outputs are rewritten in full each run, not appended. That's how dedupe works.

## 5. Acceptance tests (written and committed first, all failing before implementation)
Fixed `as_of = 2026-10-26T12:00:00Z`, brief fixtures unless noted.
| ID | Test | Expect |
|---|---|---|
| T1 / DEMO-001 | color Navy vs Blue, no submission | MISMATCH; packet exists; next step "human review: confirm approved value, prepare correction for human approval" |
| T2 / DEMO-002 | pack_count 2 vs 1, accepted 10-25 09:00, observed 10-26 09:00 | ACCEPTED_NOT_APPLIED; rank 1 in report; packet shows submission history |
| T3 / DEMO-003 | Cotton vs cotton | MATCH_FORMAT_ONLY; no packet; both raw values in report |
| T4 / DEMO-004 | item_name UNKNOWN, no time | UNKNOWN_OBSERVATION (not MISMATCH); packet says "needs more data"; next check = refresh |
| T5 / DEMO-005 | accepted 10-25, earlier Gold (observed_at blank, note 'brief gives no time'), Cream 10-26 09:00 | RESOLVED_VERIFIED based on the Cream observation only; no packet; history lists Gold as untimed and ordered before Cream; no invented timestamp anywhere in the outputs |
| T6 / DEMO-006 | accepted 10-26 08:55, last obs 10-23 Medium | PENDING_IN_WINDOW; next check 2026-10-27T08:55Z; not called a failure |
| T7 idempotent rerun | run twice on the same inputs | identical report/packet bytes; same incident ids; packet count unchanged (4) |
| T8 failed refresh | `--as-of` is run-level. (a) Add a newer `refresh_status=failed` row for DEMO-001 at fixture as-of. (b) Rerun with as-of more than 72h after the last good DEMO-001 observation | (a) DEMO-001 stays MISMATCH on the last good observation, marked stale. (b) DEMO-001 becomes UNKNOWN_NEEDS_REFRESH per §3. Never RESOLVED; untimed rows never decide status; no crash |
| T9 changed approved value | append an approved.csv row for DEMO-001 = Blue with a newer `approved_at` (history kept) | DEMO-001 → MATCH; the older Navy row/incident is SUPERSEDED, no packet, sorted last; other ids unchanged |
| T10 second marketplace | add `CA` rows for DEMO-001 (approved Navy, observed Navy) | US DEMO-001 still MISMATCH; CA DEMO-001 MATCH; separate rows and ids; never merged |
| T11 policy: no side effects | run the CLI with network sockets patched to raise | no network use; writes only under `out/` |
| T12 policy: support draft | every packet draft | marked "DRAFT — for a human to review and send"; quotes only fixture facts; contains no case number or prior-contact claim unless present in the inputs; no "we have already contacted" phrasing |
| T13 raw copy | after a run | `out/raw/` matches the input files byte-for-byte |
| T14 normalization units | whitespace/case/NFKC/int parsing; synonyms not merged | as in §3 |

## 6. File plan
```
first-light-trial/
  README.md            # run instructions, assumptions, policy boundary
  ONE_PAGER.md         # OUT OF BUILDER SCOPE (Brian/Project Lead)
  fltrial/
    __init__.py
    __main__.py        # argparse CLI: run --approved --observations --submissions --as-of --out
    load.py            # CSV loading + raw copy
    normalize.py       # §3 normalization
    classify.py        # status rules, freshness, window, priority, incident id
    render.py          # report.md/json + packet markdown + support draft template
  fixtures/
    approved.csv observations.csv submissions.csv
    variants/          # changed_value/, second_marketplace/, failed_refresh/
  tests/
    test_demo_cases.py # T1–T6
    test_rerun.py      # T7, T9
    test_refresh.py    # T8
    test_marketplace.py# T10
    test_policy.py     # T11–T13
    test_normalize.py  # T14
  out/                 # generated sample outputs; Builder commits these plus README.md
```
About 300–400 lines of code total. No dependencies beyond pytest (dev).

## 7. Time budget (Brian hands-on, 4h cap; agent time not counted)
Deadline: EOD Wed Nov 4, 2026 PT. Brian is busy Tue 7–8 AM (SaNDAI), Tue 11 AM and 7 PM classes, and his Wed 2 PM MIS 305 exam.
| When (PT) | Brian task | Time |
|---|---|---|
| Mon night / Tue early | Approve spec + answer open questions (repo, build path) | 0:15 |
| Tue (agents) | Builder: tests first → code; Review Gate pass | 0:00 Brian |
| Tue midday/afternoon | Review build, run the CLI locally, rehearse live-review edits | 0:30 |
| Tue afternoon | Edit one-pager | 0:30 |
| Wed morning | Record 5-min Loom | 0:30 |
| Wed (scheduled by Maria) | Live review | 0:30 |
| — | Buffer (fixes, re-runs, submit to Maria, Brian only) | 0:45 |
| **Total** | | **3:00 planned + 0:45 buffer = 3:45** (0:15 slack under 4h) |
Cut first if behind: Quick Builder polish, the `report.json` output, and anything beyond 2 marketplaces.
Target: build reviewed by Tue ~5 PM PT, submission sent by Wed ~1 PM PT (before the exam).

## 8. Open questions and risks
Open questions for Brian:
1. Repo: new **private** GitHub repo under Bly367 (`first-light-trial`)? This blocks Builder pushes.
2. Build path: Cursor cloud agent or the Codex paste loop?
3. OK with the Python stdlib CLI default?
4. OK with the 24h processing window, 72h freshness, and the inclusive `>=` boundary (which makes DEMO-002 a failure rather than pending)? Or prefer a longer window, which turns DEMO-002 into PENDING?
5. (Resolved by Project Lead) The DEMO-005 Gold observation has no time; it stays blank and noted.
6. When is the live review slot? It must avoid Tue classes and the Wed 2 PM exam.
7. Should agents draft the one-pager, or will Brian write it?

Risks:
- **Window/freshness choices change outcomes** (DEMO-002). Mitigation: constants in one place, printed in the report, explained in the one-pager.
- **Over-claiming causes.** Packets must separate "facts" (from fixtures) from "possible causes" (contribution conflict, schema change, processing delay, missing observation), each labeled as a hypothesis.
- **Support draft drifting into invented history.** Covered by T12; Review Gate checks it.
- **Scope creep** (web UI, real API, extra marketplaces). Out of scope; the next production step goes in the one-pager only (authorized SP-API Listings Items read + issues + notifications, after policy/role verification).
- **Brian time overrun.** The buffer is 0:45, so cut the list above early.
- **Policy boundary.** No auto listing changes or support actions. Enforced by T11/T12, and only Brian sends anything to Maria.
