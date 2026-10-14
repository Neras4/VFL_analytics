# Adapter validation

Baseline: `python -m pytest -q -p no:cacheprovider --basetemp ../work/pytest-v023-baseline-approved`: **432 passed in 12.56s**. Initial sandbox run failed with Windows temporary-directory ACL errors; no test logic was skipped.

| Input | Roster unique | Deep joined | Season joined | Accepted | Rejected | Errors | Warnings | Field conflicts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| own | 21 | 21 | 21 | 21 | 0 | 0 | 21 | 0 |
| opponent | 27 | 27 | 0 | 27 | 0 | 0 | 108 | 54 |

No duplicate roster/detail IDs and no missing/orphan detail profiles. Own season joins complete; opponent season section is absent, not a malformed export. Warnings are missing information, not rejected players: own 21 missing study percentages; opponent 27 each missing physical state, favorite style, study percentage and contract.

54 opponent conflicts are retained in evidence: 27 roster-null fatigue versus profile numeric fatigue, and 27 roster realStrength versus profile-null realStrength. Roster values, including null, win. Missing availability remains UNKNOWN for all 48 players. No label is promoted to fully studied style.

## Schema differences and fixes

- Normal has club sections that Deep omits: merge present sections recursively; preserve provenance and latest observations. Lists are whole observations, except profiles joined by stable ID. Latest roster defines membership; departed players are not resurrected.
- Profile `info.style: "Неизвестно"` is a normal missing-value sentinel, not an unsupported playing style.
- Opponent has salary/value in `info` with no contract. Fixed optional fallback that previously ignored these fields.
- Player specials are arrays with bare level-one codes; market/bid specials are space-separated strings. Separate market boundary preserves both contracts.
- Market styles expose possibleStyles sets. No single favorite style or full study is inferred.
- requested sort and applied flag differ; pagination is not a guarantee of complete results.
- Bids are timestamped independent states; no union of successive observations.
- selectedStats, rosterSeasonStats, profile minutes, contract and recent match evidence remain separate.
- Contract.current malformed structure now causes a local record error instead of an uncaught AttributeError.

Detailed field evidence and raw local diagnostics remain under ignored local_data. Public fixtures are allowlisted structural slices with replacement names/IDs/countries and financial values, no URLs, raw HTML/text, contract identities or bid amounts. Observed labels concern source structure, not generator accuracy.

Checkpoint A: full suite **458 passed in 12.31s**; after optional season-stat hardening, focused observed contract suite **26 passed in 1.18s**. Full suite repeated at next checkpoint.
