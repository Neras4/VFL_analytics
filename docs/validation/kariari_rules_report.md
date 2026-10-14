# Rules integration on observed inputs

21 own players accepted. 63 evaluations: native first position × normal/Spartak/BB, plus a position coefficient grid for every native/special slot. 46 ability tokens were parsed (bare codes normalized to level 1). Ability coefficients remain individual components; moment/economic/fatigue effects are not added to prematch force.

| Component | Result |
|---|---|
| Native and off-profile positional cells | EXACT isolated coefficients; GK/outfield restrictions checked |
| Special positions | Numerical coefficient available; tactical/formation legality separately UNKNOWN where missing |
| Form/fatigue | Available for 21 own players; 27 opponent players retain null |
| Favorite style | Labels retained; study percentage missing for all 48; no fully-known style inference |
| Captain age / Ka coefficient | Isolated published coefficient available; absolute bonus UNKNOWN without verified force bases |
| Chemistry | UNKNOWN: no verified neighbor geometry |
| Cohesion | UNKNOWN: no chronological same-season participant sets |
| Actual next-match weather | UNKNOWN |
| Weather scenario | SYNTHETIC_SCENARIO: VERY_HOT / 30°C, a published table pair, both possible style schools bounded |
| Full force / WDL | UNKNOWN; no trained outcome model |

Existing rule sources/versions remain unchanged: page159 v2.1, page40 v19.2, page64 v14.0 and packaged weather sources in manifest. No new online rule verification or generator calibration is claimed. Existing rule_reference tests check published table values, not game outcomes.

Observed own ability counts (anonymized aggregate): Ат: 10, В: 2, Д: 13, И: 2, Ка: 1, Км: 6, Л: 1, От: 2, Пд: 1, Пк: 2, Р: 1, У: 4, Шт: 1.

The partial product of nominal × form × remaining fatigue × position × style is an explicitly provisional legacy hypothesis. Its interval is conditional on this product, not a bound on the game generator. Specials, captain, donor effects and weather are reported separately; their full stacking order is unresolved. Profile realStrength is diagnostic and never silently substituted for verified positional force.

Checkpoint B: **492 passed in 15.38s**, including the original 432 cases. Focused observed/pipeline contracts: **60 passed in 1.69s**.
