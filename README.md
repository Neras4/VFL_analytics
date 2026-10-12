# VFL Analytics Engine v0.2.1

Core correctness release: AUD-01/02/03/04/05/14 corrected. Baseline: 12 tests;
current suite: 111 tests, including 99 added cases and 15 selected research
vectors. See [changes](docs/v0.2.1_changes.md), [mathematical contracts](docs/mathematical_contracts.md),
[baseline](docs/baseline_v0.1.md), [limitations](docs/known_limitations.md), and
[v0.2.2 backlog](docs/v0.2.2_backlog.md).

Usefulness is half-up rounded BEFORE youth/veteran thresholds; 93/90 minutes
is valid and gives 103%. Minimum integer minutes use T-0.5, conditional on the
final team-minute scenario. Missing study percentage remains null. Chemistry
now has explicit point/interval/unknown contracts, and interval strength is
never substituted into Decision/Transfer as a point.

**Status:** locally runnable proof of concept; **not a validated VFL generator**; **not a deployed MCP server**. The package does not log in to VFL, store credentials, make network calls, or submit lineups/bids.

This project is the first independently testable **mathematical core** discussed for Aries, Maastricht, and Kariari. It takes normalized JSON (or a compatible subset of VFL Assistant v0.5.11 JSON), computes verifiable calculations, shows uncertainty, and emits JSON suitable for future MCP wrapping.

## What's implemented

| Action | Executes now | Exact vs approximate |
|---|---|---|
| `collision` | Directed six-style collision matrix | Exact rule |
| `adapt` | Basic `roster.players` normalization from Assistant | Validates, conservative; **not yet tested against real exported JSON** |
| `lineup` | Complete 11-player assignment across selected schemes/styles, compatible position filter, favorite-style, fatigue/form, partially modeled captain/chemistry; ranks alternatives | Exact *linear subproblem*; full score is **partial estimate** |
| `opponent` | Recency/context-weighted Dirichlet-style probabilities, 90% approximate intervals, conditional collision exposure | **Approximate**, uncalibrated |
| `strategy` | Joins `lineup` + `opponent`; optional sensitivity to an *explicitly assumed* collision swing | No automatic winner unless assumption passed |
| `transfer` | Candidate's **marginal** partial lineup-strength gain, price/available cash check | Partial, no projected resale or actual win probability |
| `usefulness` | Youth growth table 16–23, 55% veteran usefulness, minimum minutes required over projected denominator | Exact thresholds; fixture availability not yet jointly optimized |

## Getting started

Python 3.11+; requires NumPy + SciPy (optional PyTest for tests).

```bash
python -m venv .venv
# Windows PowerShell: use .\.venv\Scripts\python.exe for commands below.
# Linux/macOS: use .venv/bin/python.
python -m pip install -r requirements-lock.txt
python -m vfl_analytics.cli examples/strategy.json
python -m vfl_analytics.cli examples/lineup.json
python -m vfl_analytics.cli examples/opponent.json
python -m vfl_analytics.cli examples/usefulness.json
python -m vfl_analytics.cli examples/transfer.json
python -m pytest -q -p no:cacheprovider
```

Input is one `action` request. Output is JSON. Every example uses **synthetic** players or fabricated demonstration match histories, never presented as VFL live facts.

## Key rule-backed formulas

- `S_partial = strength × (form / 100) × (1 − fatigue / 100) × known_style_factor × externally_verified_position_style_factor`
  - Real game generator includes more factors. This is a *transparent partial model*, not exact generator strength.
  - Missing fatigue/form means player is **ineligible for numeric optimization** until provided; `null` is not zero. Missing availability means **hypothetical lineup only** (`availability_unverified` warning), not submission-ready.
- Fully studied favorite style matching our style: +2.5%; incomplete studied favorite: +0.5/1/1.5/2% for 20/40/60/80%.
- Player favorite style colliding with our selected style: −1%; unknown favorite: bounded, **not assumed**. Numeric optimization for non-normal style requires a known multiplier; uncertain players remain ineligible with explicit warnings.
- Captain: rules 2.8 age bonus, only for players without unmodeled `Ка` special. 33 years: 7% of the captain's field strength added to each other player if captain >= on-field average. Captains with Ка are deliberately **not evaluated**.
- Directed chemistry links: line modifier towards player A depends on study of neighbor B. Same nationality enforces >=5%; fully known different-nationality colliding styles: −5%; equal actual styles: 12.5% × other player's study fraction. Requires **explicit lineup geometry** (`links`). Incomplete evidence returns bounds; League/empty endpoints give zero and count in the denominator.
- Youth: age-dependent useful-playing-time thresholds; in particular 16yo 20% -> +10, 17yo 28% -> +9, 18yo 38% -> +8, 19yo 44% -> +7.
- Veterans: rounded usefulness >=55% is *useful*, but bonus training requires extra qualifications (role, retirement). Feasibility is null without a separately supplied player-minute availability budget.
- Defense: zone when opponent fields >3 attacking positions; personal otherwise.

## Optimizer: precise scope

For each `(formation, style)` the initial player/slot matching solves a linear assignment using SciPy's Hungarian algorithm. It explores alternatives by excluding each selected edge and re-solving, then ranks these lineups using the included captain and chemistry effects. This is **not globally exact for nonlinear interactions**. Only native listed positions are accepted by default. No unsourced out-of-position penalties or style-color bonuses are invented. You can supply verified position-style factors via `style_position_multipliers`, but provenance should be attached in the calling application.

If style-position factors, captain special effects or geometry are missing, the result carries explicit warnings. Do not select a match tactic by partial strength score alone.

## Opponent model: precise scope

`alpha_s = prior_strength / K + Σ_i 1[style_i=s] × 2^(−days_i / half_life_days) × similarity_i`, with `K=7`, normalized to categorical style probabilities. `similarity` depends on home/away and opponent strength if supplied; those weights are **unverified modeling assumptions**. The ``posterior_alpha`` is a recency-weighted pseudo-posterior, **not** a calibrated probability model. The returned beta marginal intervals are only internal approximation under that assumed model.

Need **time-split backtesting**: proper style log-loss/Brier score against uniform, raw-frequency and recency-frequency baselines. As evidence accumulates, learn rather than guess similarity weights. Detect manager changes and tactical response to opponent/style/fixture importance. For a new manager, the prior dominates; the engine must show low confidence.

## Decision model

For each candidate our style `a` with partial lineup score `S_a`, opponent-style distribution `P(b)` and a **supplied** assumed collision swing `C` measured in the *same score units*:

`U(a) = S_a + C × Σ_b P(b) × collision_sign(a,b)`

This is a **sensitivity scenario**, not VFL's collision formula and **not** probability of winning a match. `risk_weight` penalizes standard deviation across Monte Carlo samples from the categorical pseudo-posterior; seed is fixed/reproducible. With `collision_swing = null`, the engine intentionally abstains and returns each style's `P(win collision)` / `P(lose collision)` separately.

## Source provenance

For v0.2.1, primary references are [management rules page 40](https://vfliga.com/rules.php?page=40), version 19.2, and [season rules page 70](https://www.vfliga.com/rules.php?page=70), version 14.0. Version/retrieval limitations and archive checksums are in the release documentation. SPEC_RU.md and rules_registry.json preserve the historical v0.1 research context; their unresolved claims are not new verified coefficients (see AUD-15 backlog).

VFL collector reference: [Neras4/vfl-assistant-extension](https://github.com/Neras4/vfl-assistant-extension) v0.5.11, especially `content.js` `extractJPlayers()`, `rosterCompact()`, `parsePlayerInfo()`, `mergePlayerDetails()`. This archive does **not** embed the extension or credentials.

## Roadmap (not implemented yet)

1. Validate `adapt` against representative **redacted** v0.5.11 Normal/Deep exports, preserving source `null`, and build a golden JSON contract suite.
2. Validate/encode the official positional eligibility/penalty table and style-position matrix (in rules these are also images), plus special abilities and captain Ка; only then allow a meaningful overall squad-strength comparison.
3. Add conditional coach behavior (formation, tactical transitions, substitutions) with history sourced by collector; evaluate using chronological cross-validation.
4. Calibrate actual match outcomes against real match historical data (win/draw/loss and scores) **without leaking post-match data**; no outcome model currently ships.
5. Optimize next 3–5 matches jointly, incorporate rigorously calculated fatigue changes, minutes quotas, finances, morale and injuries.
6. Wrap validated commands into authenticated, **read-only** MCP tools; deploy collector/session separately on VPS.

**Explicit exclusion:** No login, VFL cookies, MCP network transport or automatic actions are implemented. Those are separate infrastructure components.
