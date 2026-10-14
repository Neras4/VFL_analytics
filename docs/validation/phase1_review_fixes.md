# Phase 1 review fixes

All status claims are scoped to offline import and diagnostic partial calculations. Full game-force reproduction is not an acceptance criterion. No live game data were collected and no game actions were performed.

| Review item | Status | Evidence / tests |
|---|---|---|
| 1. Opponent fatigue observation loss | FIXED | Assistant 0.5.11 roster fatigue is gated on visible form; same-collection independent profile fallback. 27/27 fatigue observations recovered; form 0/27. test_review_sources: numeric/null/zero/missing/stale/conflicting cases. |
| 2. Completed scouting 5/5 | FIXED | Official page103 §7.2.1 and collector history parser verified; latest same-season style study by ID. One fully studied own favorite style; no inference for remaining 20. Date/type/player/season/rollback/conflict cases tested. |
| 3. Seven team styles | FIXED | All STYLE_NAMES before global top_n, per-style coverage, candidates, conservative values and Pareto state. test_all_styles_survive_top_one. |
| 4. Candidate explanations | FIXED | Bounded same-slot replacements and pair swaps; raw normalized inputs, factors, proxy delta, conditional interval and unknown mechanisms. test_explanations_preserve_same_geometry_and_specials; no artificial specialty force total. |
| 5. Multi-team isolation | FIXED | Group by kind/ID/current season; ID filter; 13202/22931/748 synthetic isolation, same-ID own/opponent isolation and season rejection tests. Real additional clubs are not claimed validated. |
| 6. Compact / detailed / raw output | FIXED | Main summary 675177 bytes versus prior 18129449 bytes. Optional details.json 10740174 bytes. Raw diagnostics off by default. Trusted resolved project-local root, traversal and symlink escape tests. |
| 7. Test preservation and CI | FIXED | Baseline 496; final 530. Existing assertions updated only for requested fatigue semantics, 7-style coverage and stricter missing-season merge rejection. No tests removed. Python 3.11/3.12 CI required before merge. |
| 8. Reports and PR | FIXED | Existing PR #3 and version 0.2.3 retained, checkpoints D/E/F. Public reports use checked aggregate/anonymous inputs; detailed names, IDs, paths and finances remain local. |

## Source evidence

[Collector source](https://github.com/Neras4/vfl-assistant-extension/blob/main/content.js), version 0.5.11; immutable content blob SHA and parser findings are in review_source_evidence.json. Roster null is not zero; top-level detail fatigue is a roster copy, not a second independent observation. Profile collectedAt is unavailable in real data: generatedAt is only a collection reference assigned before the Deep fetch. Fallback identifies this timing limit rather than inventing exact observation times.

[Official scouting rule](https://vfliga.com/rules.php?page=103), §7.2 and §7.2.1: favorite style is immutable and five completed style stages reveal it fully. Stages are states, not additive records. Other study types cannot verify favorite style.

## Remaining scope limits

Full generator force, full modifier order/bases, verified match availability, complete formation catalog/tactical context, chemistry geometry, participant history/cohesion, target weather and trained WDL remain UNKNOWN. No quantitative full-model sensitivity bound is fabricated. Equal proxy values do not prove equal game efficiency. Within the diagnostic scope, Phase 1 is ready for review/merge once final CI is green; no automatic merge.
