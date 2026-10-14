# Observed export inventory — 2026-10-14

Nine authorized Assistant 0.5.11 snapshots were inspected locally. Public labels anonymize club/player identities. Raw source bytes, exact absolute paths, SHA256 and all nested collection timestamps are in ignored `local_data/reports/v0.2.3/validation.json`; readable paths are in `inventory.md` beside it. No raw exports are published.

| Alias | Kind/depth | Generated UTC | Bytes | Roster | Deep | Season |
|---|---|---|---:|---:|---:|---:|
| export-1 | vfl-opponent-context/deep | 2026-10-14T15:57:06.105Z | 126639 | 27 | 27 | 0 |
| export-2 | vfl-opponent-context/normal | 2026-10-14T15:56:59.661Z | 42224 | 27 | 0 | 0 |
| export-3 | vfl-own-team-context/deep | 2026-10-14T15:56:28.271Z | 229777 | 21 | 21 | 21 |
| export-4 | vfl-own-team-context/normal | 2026-10-14T15:56:09.198Z | 75608 | 21 | 0 | 21 |
| export-5 | vfl-transfer-bids/n/a | 2026-10-14T15:58:46.968Z | 3779 | 0 | 0 | 0 |
| export-6 | vfl-transfer-bids/n/a | 2026-10-14T15:58:02.085Z | 584 | 0 | 0 | 0 |
| export-7 | vfl-transfer-market/n/a | 2026-10-14T15:57:43.018Z | 122023 | 0 | 0 | 0 |
| export-8 | vfl-transfer-market/n/a | 2026-10-14T15:57:59.853Z | 89415 | 0 | 0 | 0 |
| export-9 | vfl-transfer-market/n/a | 2026-10-14T15:57:31.199Z | 1613 | 0 | 0 | 0 |

Own Normal contains finances, deals and teamStatistics absent from Deep. Both contain management; Deep adds playerDetails. All sections survive the join. Opponent has recentMatches text, not parsed historical starting-player sets. Own has 21 contracts; opponent has no contract section. Market search and bids are distinct management observations.

Classification: OBSERVED structure/counts. Financial and bid details stay local.
