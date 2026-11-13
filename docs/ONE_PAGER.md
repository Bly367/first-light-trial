# Catalog Issues Checker: One-Page Summary

**The problem.** A brand's approved product details sometimes differ from what its Amazon listing shows. Amazon can accept a fix and the listing can still stay wrong, so someone has to check by hand.

**Approaches compared.** We looked at three options:
- **Notebook** (a document that mixes code and results): good charts, but reruns are fragile.
- **No-code workflow** (spreadsheet plus an automation service): visual, but hard to test, and it needs outside accounts and logins.
- **Python command-line tool** (a small program run with one typed command): **chosen.** It runs the same way every time, has automated tests, and needs no outside accounts.

**What it does.**
1. **Inputs:** three spreadsheet files (CSV): approved values, timestamped listing snapshots, and the history of submitted fixes.
2. **A status for each SKU** (SKU = the seller's product code), such as mismatch or still pending.
3. **Outputs:** a report ranked by urgency; an evidence packet for each open problem with facts, possible causes, and a next step; and a draft support message that a human reviews and sends. Rerunning creates no duplicate problems. The report and packets explain, in plain language, why each status was chosen and why a nearby alternative was not.

**Demo results** (from the tool's saved sample output in the code, `out/report.md`):

| SKU | Approved vs. seen | Result | Who acts |
|---|---|---|---|
| DEMO-001 | Navy vs. Blue | Mismatch | Human review |
| DEMO-002 | 2 vs. 1, fix accepted | Fix accepted, not applied | Human review, top priority |
| DEMO-003 | Cotton vs. cotton | Match (formatting only) | None |
| DEMO-004 | Studio Bowl vs. unknown | No usable observation | Needs more data |
| DEMO-005 | Cream vs. Cream | Fixed and verified | None |
| DEMO-006 | Large vs. Medium (old) | Waiting, fix in progress | Needs more data |

**Assumptions.**
- Values are compared after ignoring case and extra spaces (plus standard character forms, and "2" equals "2.0" for counts). Similar words are not treated as the same: Navy is not Blue.
- An observation older than 72 hours is too old to confirm anything.
- Amazon gets 24 hours to apply an accepted fix. Before then, the result is "pending," not "failed." DEMO-002 was checked exactly 24 hours after its fix was accepted, so it counts as not applied.
- If an accepted fix has no timestamp, the tool still shows a confirmed mismatch and only flags that the acceptance time is missing; it does not replace the mismatch with "needs a refresh." Without the time, it also can't call the fix pending, not applied, or verified.

**Data limits.** Everything is invented test data. The submission and snapshot IDs are made up, and the files say so. The tool does not connect to Amazon.

**Safety boundary.** The tool never changes a listing. It never opens, sends, or answers a support case. People own all support cases.

**Next production step.** First, confirm Amazon's current rules, the approved account permissions, and the official data connections (APIs). Then replace the test files with approved reads of real listings and Amazon's issue alerts.
