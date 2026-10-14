# VFL Assistant data contract and gaps

Static source: https://github.com/Neras4/vfl-assistant-extension/blob/main/content.js,
blob321ef4abdef9e22ed46068780a7d5feade4f059b, inspected2026-10-12. Assistant unchanged.
Fixtures are SYNTHETIC replicas of available code structures. **No real Normal/Deep
exports were accepted or labeled OBSERVED**; this is v0.2.3 work.

| Field/need | Source behavior | Engine handling |
|---|---|---|
| Identity | roster uses id; details and subtrees playerId | Positive numeric collector ID normalized to string; no name join |
| Duplicate/orphan detail | Ambiguous join possible | Issues reported; duplicates not last-writer-wins |
| Form/fatigue/realStrength | Roster is current-state authority | Present roster key, including null, wins over older profile copies |
| Missing form/fatigue | Opponent/Normal visibility may be limited | null; eligible candidate retained with UNKNOWN force and explicit search proxy |
| favorite style | Deep info.style is text; ambiguity possible | Label retained if supported; never implies verified identity/100% study |
| Study percentage | No structured exact study field in inspected export | null; explicit normalized fields supported when supplied separately |
| Specials | Current roster array of rendered codes | Known code/level validation; bare recognized code -> level1; absent field specials_known=false |
| Contract/salary/value | Deep contract.current and info fields | Missing remains null; contract evidence retained separately |
| Player season minutes | info.seasonMinutes is competitive season total | Never derive minutes from games or selectedStats |
| selectedStats | User-selected tournament/season scope | Retained separately with source scope |
| rosterSeasonStats | all-tournament scope, sort300, season | Joined by ID as distinct evidence; scope checked, not replaced with selectedStats |
| recentMatches | Compact text; not normalized all-participant history | Retained as evidence; not automatically fed into cohesion/opponent training |
| management | Separate optional scope | Not converted into players, availability or confirmed training resources |

Required data not established by current exporter:

- Target-match competition-specific injury/suspension availability.
- Exact hidden style identity/remaining candidates and study percentage evidence.
- Verified real force for each player on each assigned position, at the correct
  stage for captain/И/Л; current displayed realStrength is diagnostic only.
- All participants (including substitutions), same-season latest-first order
  and competitive flag for up to25 preceding cohesion matches.
- Full legal formation/tactical-permission context and League/reserve constraints.
- Owner-at-end-season team-minute denominator, transfer/national-team numerator
  semantics and playable future minute budget.
- Weather/temperature scenario, real-player status, mood, home attendance and
  unknown modifier order. Contract completeness needed for any economic forecast.

Normalized callers can supply these contexts explicitly. The core never infers
them from a stale snapshot, count of matches, singleton style label or raw text.


v0.2.3 update: see validation/kariari_data_gaps.md and kariari_adapter_report.md for observed Normal/Deep results. Original synthetic limitations above are historical; no match-generator validation has been established.
