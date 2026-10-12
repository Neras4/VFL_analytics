# Calculation pipeline v0.2.2

1. Validate normalized input: IDs, unique players, native positions/combinations,
   finite numeric values, 75–125 form, 0–100 fatigue, age16–34, specialties/levels.
   Collector absence and malformed data are different states.
2. Verify/load versioned package data using SHA256 and schema/domain checks.
3. Establish GK/outfield eligibility and published position suitability. Check
   explicit base-slot transformations and SW condition; CM tactical permissions
   remain unknown unless supplied. Missing availability never confirms eligibility.
4. Compute isolated form, fatigue, position and favorite-style components.
   A partial search product is explicitly ESTIMATED/BOUNDED. Unknown form/style
   does not remove a legally eligible player; nominal/known-physical proxy is
   an explicit candidate-generation assumption, not an imputed missing modifier.
5. Look up position/team-style color separately. No numerical color coefficients.
   Report all specialty components by prematch, conditional, moment, fatigue,
   development/economic scopes. Never sum these into one prematch-strength value.
6. Compute interpersonal chemistry over supplied lines, preserving intervals
   and zero endpoints. Compute team cohesion from distinct chronological participant
   history; latest first, same season, competitive matches, max25, stop overlap<4.
7. Weather lookup uses **actual favorite PLAYER style**, nominal strength and an
   exact weather/temperature pair. It is a displayed strength value, not a factor.
   Unknown player style can yield a two-school range; no midpoint. Never apply
   weather again to a strength already adjusted by weather or other modifiers.
8. Captain/Ka and individual donor deltas require explicit verified current real
   positional/moment force inputs. `realStrength` collector text alone is insufficient.
   Captain weakness gate uses exact rational comparison; self is excluded from delta.
9. Return PlayerEvaluation with components, sources, partial range, unresolved
   modifiers and UNKNOWN total force. Full combination order is not demonstrated.

## Bounded lineup search

Hungarian assignment generates candidates using an explicit search proxy;
one-edge exclusions add up to11 alternatives. Transfer incumbents are independently
rechecked and reevaluated under the same plan/style/context/objective. Constraints:
<=200 players, <=32 supplied plans, seven distinct team styles, <=224 incumbents.

`known_components`: heuristic proxy ranking plus published chemistry on the
provisional product. Captain, donors, cohesion and all player components are
returned separately; they are not silently stacked into that scalar.

`conservative`: explicitly selects a lower bound of the **conditional partial
model**. This is ESTIMATED as an objective, never guaranteed full generator force.
When a conditional range is unavailable, no conservative guarantee is reported.

`pareto`: robust interval dominance of partial-model force, isolated captain
component and cohesion. A candidate dominates another only if every comparable
lower bound is >= the other's upper bound and at least one is strictly greater.
Unknown nonlinear axes prevent dominance. The output reports any top_n truncation.
Equal or incomparable candidates are retained, with no final recommendation.

Bounds may be conservative because hidden styles of multiple links are dependent.
No global nonlinear-optimum guarantee. `lineup_eligibility.status=UNKNOWN` marks
the remaining full formation/reserve context even when the known constraints pass.

## Transfer and decisions

The previous feasible incumbent remains available after roster expansion. A new
candidate can be unused. `estimated_search_delta` compares the same explicit
heuristic objective, with an invariant against negative pruning artifacts.
`marginal_partial_strength_result` is ESTIMATED or UNKNOWN, never exact full benefit.
Financial affordability is price vs cash only; `economic_value=UNKNOWN`.
Decision abstains on point-force absence. A supplied collision swing remains a
scenario assumption; collision direction is exact, magnitude is unpublished.
