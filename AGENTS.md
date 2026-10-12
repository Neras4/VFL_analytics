# AGENTS.md — VFL Analytics Engine

## Mission and working context

You are the coding agent for **VFL Analytics Engine**, an independently testable, rules-first analytical engine for the browser football manager Virtual Football League (VFL, https://vfliga.com/).

- **This repository:** `Neras4/VFL_analytics`; Python 3.11+; package `vfl_analytics/`; JSON-in/JSON-out entrypoint `vfl_analytics.cli`.
- **Data collector (separate project):** `Neras4/vfl-assistant-extension` (VFL Assistant). It provides snapshots of teams, players, matches, finances and management. This repository consumes its exports; it does not control the browser or the VFL website.
- **User's clubs for eventual real-world validation:** Ariès (`22931`), Maastricht (`748`), Kariari-Pokochi (`13202`). Do not assume their live state is known from old files or discussions.
- **Research corpus:** `VFL_Analytics_Research_Specification_2026-10-10(1).zip` when supplied locally, and `all_rules.md` / `all_rules(1).md` when available. These are reference materials, **not executable truth**: validate formulas, versions, source links and classifications before coding them.
- **Current baseline at the beginning of v0.2.2 work:** v0.2.1 on `main` (reported 111 tests). Verify the actual branch, version and test results at the beginning of every task; do not assume the baseline is unchanged.

**Primary goal:** produce correct, traceable, deterministic mathematical components and honest, uncertainty-aware recommendations. Never confuse a partial model with VFL's closed match generator.

## Start of every task

1. Inspect `git status`, current branch, `pyproject.toml`, `README.md`, `CHANGELOG.md`, `docs/known_limitations.md`, `docs/mathematical_contracts.md`, `docs/v0.2.2_backlog.md` (or their successors), and the files relevant to the request.
2. Identify whether the user requested research, implementation, review, or deployment. Work **only** within that scope. A version roadmap is not permission to implement every future feature.
3. Locate any supplied research ZIP or source documents **inside the accessible workspace**. If unavailable, report the missing inputs; never invent a path, a coefficient, or successful verification. Continue independently possible work.
4. Run the existing tests before changes. Record the command, result and any environment issues. If dependencies are missing, attempt a reproducible isolated installation when permitted.
5. Make a short, ordered implementation plan and define testable acceptance criteria. Then implement without unnecessary confirmation requests.

## Non-negotiable mathematical rules

### Evidence and provenance

- **Official VFL rules are primary evidence** for published mechanics. Cite page/section, version/date when known, and the exact source of each constant, table, or formula.
- Research exports (`coefficients.json`, `match_coefficients.json`, `special_abilities.json`, `weather_coefficients.json`, `image_extractions.json`, `test_vectors.json`) are intermediate derived artifacts. Check their units, domains, shape, semantics and consistency with source material before importing.
- Record source provenance alongside machine-readable rule data. Keep rule version separate from the engine software version.
- Treat embedded image colors as **qualitative** unless the rule explicitly provides numeric values. `special_bonus`, `bonus`, `neutral`, `penalty`, `strong_penalty` are categories, not invented multipliers.
- Document contradictions or inaccessible evidence as `CONFLICT`/`UNKNOWN`; never silently pick whichever formula is easier to implement.
- Clearly separate: published rule, mathematical derivation, synthetic example, observed VFL behavior, and statistical hypothesis.

### Exactness and missing data

Use the existing `CalculationResult` / `ResultStatus` conventions:

- `EXACT`: an **isolated** component is exact under stated, verified inputs and published rules; does **not** imply exact total match strength.
- `BOUNDED`: justified lower and upper bounds; not a confidence/credible interval.
- `ESTIMATED`: explicitly assumed or learned point estimate, with model assumptions stated.
- `UNKNOWN`: data or rules insufficient.
- `NOT_APPLICABLE`: rule does not apply.

**Unknown is not zero, a midpoint, the lower bound, or a default multiplier of one.** Do not silently convert `null` into any of these. Do not use a component interval as a point estimate without an explicit, documented scenario/mode. Preserve uncertainty through adapters, optimizers, decisions and CLI JSON.

- Distinguish `strength`, `realStrength`, nominal strength, position-adjusted strength, partial pre-match estimate, in-match strength and final team strength.
- Keep position eligibility/penalty **separate** from team-style positional color category.
- Keep favorite player style **separate** from chosen team style, and from percentage of study/verification.
- Keep interpersonal **chemistry** separate from seasonal **cohesion/played-together** bonuses.
- Keep style collision **direction** separate from the **unknown magnitude** of the collision effect.
- Keep ordinary strength specials separate from **moment-specific, conditional, economic and fatigue** effects; do not add them into one strength number.
- Do not assume modifier addition/multiplication/order unless confirmed. If order is not published, return components and an explicit limitation rather than manufactured totals.
- Keep `%`, ratio, `fraction`, absolute strength points, minutes and currency distinguishable in API and tests.
- Avoid binary floating-point at threshold decisions and halfway rounding; prefer exact integer/rational/Decimal arithmetic for rule boundaries.
- Validate external numeric data: reject NaN/Infinity, inappropriate booleans, invalid negative values, malformed intervals, fractional ages/minutes and impossible states. Allow **documented** exceptional cases, such as player minutes greater than the club's official minutes.

### Optimization

- **Eligibility is not score certainty.** An unknown favorite style must not automatically make a legally eligible player ineligible. Keep a candidate with `BOUNDED`/`UNKNOWN` score or separate explicit heuristic ranking.
- Keep constraints explicit: unique player IDs; 11 starters including 1 GK; allowed positions/formations; known injuries/suspensions; scope of lineup availability checks.
- Hungarian/linear assignment is exact only for the **linear assignment subproblem**. Captain/chemistry/cohesion are nonlinear; candidate reranking is not proof of a global optimum.
- Preserve the best previously feasible **incumbent** when adding a transfer candidate. Compare like-for-like under the same objective, style, plan and constraints. A new candidate may be unused.
- If evidence cannot rank alternatives unambiguously, return comparable components, ranges and non-dominated choices, or abstain. Do not fabricate a single "best" team.
- Do not claim win/draw/loss probabilities are calibrated before chronological backtesting. Opponent style distributions and collision-swing scenarios remain hypotheses until validated.
- Search boundedly and monitor execution time; no unbounded enumeration of formations × players × special cases.

## Source contracts and boundaries

- `vfl_analytics/adapters.py` is the **boundary** between external collector JSON and typed internal models. Isolate schema drift there; avoid collector-specific keys sprinkled across `rules.py`, `lineup.py`, etc.
- Identity joins use normalized `playerId`/ID strings. Detect duplicate, missing, incompatible IDs; never join players by name.
- Roster current-state fields (fatigue, form, form trend, real strength) take priority over duplicate values from `playerDetails`. Do not overwrite authoritative roster state with older profile copies.
- `selectedStats` is the user-selected page scope. `rosterSeasonStats` is the separate all-tournament season aggregation. Do not confuse them.
- Own Normal/Deep, opponent Normal/Deep, Club Data, Management, Transfer Market and My Bids have different schemas and availability; do not assume every field exists everywhere.
- Missing study percentage is `null`, not 0%. Seeing a style label does not prove 100% study or the true hidden favorite style.
- Preserve `null` and raw/source evidence where valuable for diagnostics. Never log credentials, cookies or private session information.
- Golden fixtures built from **synthetic** examples are `SYNTHETIC`, not proof of compatibility with real VFL exports. Only label validation `OBSERVED` when real game data were actually inspected and provenance captured.
- **Do not edit the VFL Assistant repository** unless the user explicitly assigns a separate task there.

## Code quality and test policy

- Make the smallest cohesive changes that solve the task; prefer typed, pure mathematical functions with deterministic output.
- Separate large numerical rule tables from logic. Load versioned data files with validation rather than duplicating constants through modules.
- Avoid excessive new dependencies and architecture rewrites. Use existing NumPy/SciPy and pytest unless a new dependency is justified.
- Maintain public JSON compatibility when possible. When impossible, document breaking changes in `docs/mathematical_contracts.md` or its successor and update **all** consumers and examples.
- Every new rule must have a source and tests covering: normal case; boundaries; unknown input; invalid input; and combined cases **only where combination is supported**.
- Keep pytest categories meaningful:
  - `rule_reference`: an actual published example or reference table value;
  - `synthetic`: invented data testing valid arithmetic/logic;
  - `observed`: real, sourced VFL records.
- Do not relabel synthetic tests as observed, or call green unit tests validation of the hidden match generator.
- Add regression tests for bugs. Include tests for null propagation, result status, type and unit, not merely numeric equality.
- Validate optimizer invariants and transfer incumbent/monotonicity properties where the objective is truly comparable.
- Test CLI JSON-in/JSON-out and offline operation. CI must pass without VFL login, live website access or local-only file paths.
- For performance-sensitive search, provide a small reproducible benchmark, representative of 20–30 players, with bounded runtime and without falsely promising a global optimum.

## Recommended verification commands

Run from the repository root using the active virtual environment:

```bash
python -m pip install -e '.[test]'
python -m pytest -q -p no:cacheprovider
python -m vfl_analytics.cli examples/lineup.json
python -m vfl_analytics.cli examples/strategy.json
python -m vfl_analytics.cli examples/usefulness.json
```

On Windows PowerShell use `py -m ...` or the virtual-environment interpreter instead of assuming `python` points to the intended version. Pin/lock dependencies reproducibly; do not require an environment-specific `Scripts/` path in source or CI.

If an action fails, report the **actual command, error and impact**. Do not claim a test was run because README, an earlier agent or a PR says it passed.

## Git, checkpoints and scope control

- Work from the latest verified base branch, normally `main`. Use a task branch such as `feature/analytics-v0.2.2` unless the user specifies another branch.
- Do not overwrite unrelated local changes or delete untracked work. If the worktree is dirty, inspect it before modifying files.
- For multi-stage work, commit coherent checkpoints. For v0.2.2 use:
  1. **A: Core hardening** — input validation, collector-adapter contract, CI, eligible unknown-style players, transfer incumbent.
  2. **B: Rules expansion** — verified positional rules, qualitative style matrix, special-ability components, weather lookup, captain/Ka, chemistry/cohesion.
  3. **C: Integration and validation** — uncertainty-aware evaluation/optimization, tests, benchmarks, documentation.
- Do not mark a checkpoint complete without running relevant tests; record the outcome even if blocked.
- Never commit `.venv`, caches, secrets, large temporary extracted research trees, or user-specific raw exports. Only commit compact, necessary, properly attributed rule data and fixtures.
- Do not push, open a PR, merge, deploy or make changes outside this repository **unless explicitly authorized in the task**. If a task authorizes a PR, create it after tests; **never merge it automatically**.
- Keep `CHANGELOG.md`, package version, README, known limitations, rule coverage and backlog synchronized with actual implementation.
- Do not silently extend v0.2.2 to model training, MCP hosting, website login, transfers or automatic lineup submission. Those require separate work and authorization.

## Security and VFL actions

This project is read-only analysis. Do **not** log into VFL, export cookies, scrape using a personal session, submit lineups, change tactics on the site, bid on players, purchase players, modify accounts or deploy services unless a separate, explicit user request covers the action and its boundaries.

Never put credentials, tokens or session material in Git, fixtures or logs. Keep optional collector integration test data anonymized and minimized. Prefer synthetic/offline tests while implementation is under review.

## Before handing work back

Report concisely, with evidence:

1. Completed scope and files changed.
2. Checkpoint commit SHAs and branch/PR URL **if actually created**.
3. Tests and benchmarks actually executed, including exact pass/fail counts and commands.
4. Rule coverage added, with source/versions and statuses (`EXACT`/`BOUNDED`/`ESTIMATED`/`UNKNOWN`).
5. Breaking API changes and data-schema changes.
6. Unresolved AUD items, blockers and why they remain open.
7. Explicit next step. For v0.2.2, real VFL Assistant exports and historical match backtesting belong to **v0.2.3**, not to a fabricated acceptance claim now.

**Never say "fully accurate", "generator reproduced", "real-world validated", "all rules implemented" or "all tests pass" without evidence covering the exact claim.**
