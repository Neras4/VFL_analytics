# Lineup smoke tests — observed inputs, provisional model

Three candidate geometries × normal/Spartak/BB × known_components/conservative/pareto. Every returned assignment has 11 unique IDs and exactly one GK. Repeated runs match byte-equivalent JSON values. Availability and full formation legality remain UNKNOWN; no final recommendation.

P01…P21 are local one-to-one anonymous player labels; the private mapping is not published. All scores use partial_strength_units and exclude unresolved mechanics.

| Mode | Candidates before limit | Returned | Deterministic |
|---|---:|---:|---|
| known_components | 9 | 9 | True |
| conservative | 9 | 9 | True |
| pareto | 81 | 9 | True |

Pareto has 81 nondominated candidates because unknown captain/cohesion axes cannot establish robust dominance; top_n=9 truncates the output. Its display order is the explicit partial proxy, not a dominance proof. Conservative mode uses the conditional lower bound where available. Opponent conservative comparisons are UNKNOWN, with diagnostic proxy ordering only.

| Mode | Style | Geometry | Partial / interval | Assignment (anonymous) |
|---|---|---|---|---|
| known_components | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P19, RM=P10, AM=P20, CF=P17 |
| known_components | spartak | 4-4-1-1 | [978.880, 1013.487] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |
| known_components | bb | 4-4-1-1 | [978.880, 1013.487] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |
| known_components | normal | 4-1-3-1-1 | 985.357 | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| known_components | spartak | 4-1-3-1-1 | [975.504, 1009.991] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| known_components | bb | 4-1-3-1-1 | [975.504, 1009.991] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| known_components | normal | 4-4-2 | 980.582 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P20, RM=P10, CF1=P19, CF2=P17 |
| known_components | spartak | 4-4-2 | [970.777, 1005.097] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P20, CM2=P19, RM=P10, CF1=P21, CF2=P17 |
| known_components | bb | 4-4-2 | [970.777, 1005.097] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P20, CM2=P19, RM=P10, CF1=P21, CF2=P17 |
| conservative | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P19, RM=P10, AM=P20, CF=P17 |
| conservative | normal | 4-1-3-1-1 | 985.357 | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| conservative | normal | 4-4-2 | 980.582 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P20, RM=P10, CF1=P19, CF2=P17 |
| conservative | spartak | 4-4-1-1 | [978.880, 1013.487] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |
| conservative | bb | 4-4-1-1 | [978.880, 1013.487] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |
| conservative | spartak | 4-1-3-1-1 | [975.504, 1009.991] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| conservative | bb | 4-1-3-1-1 | [975.504, 1009.991] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, DM=P17, CM=P21, RM=P10, AM=P20, CF=P19 |
| conservative | spartak | 4-4-2 | [970.777, 1005.097] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P20, CM2=P19, RM=P10, CF1=P21, CF2=P17 |
| conservative | bb | 4-4-2 | [970.777, 1005.097] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P20, CM2=P19, RM=P10, CF1=P21, CF2=P17 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P19, RM=P10, AM=P20, CF=P17 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P04, CD1=P06, CD2=P07, RD=P09, LM=P03, CM1=P17, CM2=P21, RM=P10, AM=P20, CF=P19 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P06, CD2=P07, RD=P09, LM=P04, CM1=P17, CM2=P21, RM=P10, AM=P20, CF=P19 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P06, CD2=P07, RD=P09, LM=P04, CM1=P21, CM2=P19, RM=P10, AM=P20, CF=P17 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P21, CM2=P19, RM=P10, AM=P20, CF=P17 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P19, CM2=P17, RM=P10, AM=P20, CF=P21 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |
| pareto | normal | 4-4-1-1 | 988.767 | GK=P02, LD=P03, CD1=P07, CD2=P06, RD=P09, LM=P04, CM1=P21, CM2=P17, RM=P10, AM=P20, CF=P19 |
| pareto | spartak | 4-4-1-1 | [978.880, 1013.487] | GK=P02, LD=P04, CD1=P07, CD2=P06, RD=P09, LM=P03, CM1=P19, CM2=P21, RM=P10, AM=P20, CF=P17 |

Normal leading candidate: estimated subtotal 988.767. Same proxy under Spartak/BB yields a conditional [978.880, 1013.487] interval, with partial_total=null. These ties arise from missing study evidence and omitted effects; they do not establish style equivalence in the game.

For all candidates: known positional/form/fatigue components are reported; style ability coefficients are separate. The search proxy does not stack those ability coefficients into its total, because the full modifier order/base is unresolved. Captain/И/Л absolute deltas, chemistry, cohesion and target weather are UNKNOWN. Special CM→DM/AM context is unverified. All eligibility statuses remain UNKNOWN, even when linear assignment constraints pass.

Own/opponent smoke: 21 vs 27 normalized players, no player losses; opponent physical state unknown for all 27. No W/D/L probabilities, game actions or definitive match recommendation.
