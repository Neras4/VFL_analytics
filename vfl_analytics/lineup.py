"""11-slot lineup optimization: exact linear assignment + local candidate re-ranking.
Complex generator parameters / position style tables are NOT silently manufactured.
"""
from __future__ import annotations
from collections import defaultdict
import numpy as np
from scipy.optimize import linear_sum_assignment
from .models import Player, PositionPlan, STYLE_NAMES, base_position
from .rules import baseline_strength, captain_bonus, chemistry_for_player, MATCH_SOURCE
from .results import ResultStatus, CalculationResult, bounded, unknown


def _factor(plan: PositionPlan, style: str, slot: str) -> float:
    table = plan.style_position_multipliers.get(style, {})
    return table.get(slot, table.get(base_position(slot), 1.0))


def _build_matrix(players: list[Player], plan: PositionPlan, style: str):
    matrix = np.full((11, len(players)), -1e9)
    field_warnings = set()
    if style not in plan.style_position_multipliers:
        field_warnings.add("position_style_table_missing: position/style effects omitted")
    for si, slot in enumerate(plan.slots):
        for pi, p in enumerate(players):
            if p.available is False or base_position(slot) not in p.positions:
                continue
            if p.available is None:
                field_warnings.add(f"availability_unverified:{p.id}")
            strength, missing = baseline_strength(p, style, _factor(plan, style, slot))
            if strength is None:
                for m in missing:
                    field_warnings.add(f"{m}:{p.id}")
                continue
            for m in missing:
                field_warnings.add(f"{m}:{p.id}")
            matrix[si,pi] = strength
    return matrix, sorted(field_warnings)


def _solve_assignment(matrix: np.ndarray, banned: tuple[int,int] | None = None):
    work = matrix.copy()
    if banned:
        work[banned[0],banned[1]] = -1e9
    rows, cols = linear_sum_assignment(-work)
    if len(rows) != 11 or np.any(work[rows,cols] <= -1e8):
        return None
    return {int(s):int(p) for s,p in zip(rows, cols)}


def _evaluate(players: list[Player], plan: PositionPlan, style: str,
              matrix: np.ndarray, assign: dict[int,int]) -> dict:
    mapping = {plan.slots[si]: players[pi] for si,pi in assign.items()}
    by_id = {p.id: float(matrix[si,pi]) for si,pi in assign.items() for p in [players[pi]]}
    warnings = set()
    chem_add = 0.0
    chem_low = chem_high = 0.0
    chemistry_uncertain = False
    chemistry_components = {}
    if plan.links:
        neighbors = defaultdict(list)
        for u,v in plan.links:
            if u not in mapping or v not in mapping:
                raise ValueError(f"Unknown link slot {u}->{v}")
            neighbors[u].append(mapping[v]); neighbors[v].append(mapping[u])
        for slot, p in mapping.items():
            mod, uncertain_count = chemistry_for_player(p, neighbors.get(slot, []))
            chemistry_components[p.id] = mod.to_dict()
            if uncertain_count:
                warnings.add(f"chemistry_unknown:{p.id}")
                chemistry_uncertain = True
            if mod.status == ResultStatus.EXACT:
                chem_add += by_id[p.id] * mod.value
                chem_low += by_id[p.id] * mod.value
                chem_high += by_id[p.id] * mod.value
            elif mod.status == ResultStatus.BOUNDED:
                chem_low += by_id[p.id] * mod.lower
                chem_high += by_id[p.id] * mod.upper
    else:
        warnings.add("chemistry_links_not_provided")
    captains = []
    for p in mapping.values():
        try:
            captains.append((captain_bonus(p,by_id),p))
        except ValueError:
            warnings.add("captain_Ka_special_unmodeled")
    best_captain = max(captains, key=lambda x:x[0]) if captains else (0.,None)
    baseline = sum(by_id.values())
    subtotal = baseline + best_captain[0] + chem_add
    if not plan.links:
        chemistry_result = unknown(unit="partial_strength_units", source=MATCH_SOURCE,
            reason="Line geometry not supplied; chemistry omitted from subtotal")
    elif chemistry_uncertain:
        chemistry_result = bounded(chem_low, chem_high, unit="partial_strength_units", source=MATCH_SOURCE,
            reason="Bounds conditional on provisional partial strengths; not generator force")
    else:
        chemistry_result = CalculationResult(ResultStatus.ESTIMATED, value=chem_add,
            unit="partial_strength_units", source=MATCH_SOURCE,
            reason="Published point modifiers applied to modeled partial strengths")
    if chemistry_uncertain:
        warnings.add("ranking_uses_known_component_subtotal; uncertain chemistry omitted explicitly")
    return {
        "style":style, "lineup": [{"slot":slot,"player_id":p.id,"name":p.name,
                                 "partial_strength":round(by_id[p.id],3)}
                                for slot,p in mapping.items()],
        "linear_strength": round(baseline,3),
        "included_chemistry_bonus":None if chemistry_uncertain else round(chem_add,3),
        "chemistry_components":chemistry_components,
        "chemistry_bonus_result":chemistry_result.to_dict(),
        "included_age_captain_bonus":round(best_captain[0],3),
        "captain_id":best_captain[1].id if best_captain[1] else None,
        "partial_total":None if chemistry_uncertain else round(subtotal,3),
        "ranking_score":round(subtotal,3),
        "ranking_score_result":CalculationResult(ResultStatus.ESTIMATED, value=round(subtotal,3),
            unit="partial_strength_units", reason="Explicit known-component subtotal for heuristic ranking; not interval midpoint").to_dict(),
        "warnings":sorted(warnings)
    }


def optimize_lineups(players: list[Player], plans: list[PositionPlan],
                     styles: list[str] | None = None, top_n: int = 3) -> dict:
    if top_n < 1:
        raise ValueError("top_n must be >= 1")
    if len(set(p.id for p in players))!=len(players):
        raise ValueError("Duplicate player IDs")
    styles = styles or list(STYLE_NAMES)
    all_results = []
    invalid = []
    for plan in plans:
        for style in styles:
            matrix, warnings = _build_matrix(players,plan,style)
            best = _solve_assignment(matrix)
            if best is None:
                invalid.append({"style":style,"slots":list(plan.slots),
                                "reason":"No eligible complete 11-player assignment"})
                continue
            candidates = [best]
            # Re-solve forbidding one optimal edge: multiple candidate assignments,
            # then re-rank including known captain and chemistry effects.
            for s,p in best.items():
                alt = _solve_assignment(matrix,(s,p))
                if alt is not None and alt not in candidates:
                    candidates.append(alt)
            evaluations = [_evaluate(players,plan,style,matrix,assn) for assn in candidates]
            leader = max(evaluations, key=lambda d:d["ranking_score"])
            leader["slots"] = list(plan.slots)
            leader["variants_considered"] = len(candidates)
            leader["warnings"] = sorted(set(leader["warnings"]+warnings))
            all_results.append(leader)
    all_results.sort(key=lambda r:r["ranking_score"],reverse=True)
    return {
        "status":"partial_model" if all_results else "no_valid_lineup",
        "optimization":"exact_linear_assignment_plus_one_edge_exclusion_reranking; not guaranteed global nonlinear optimum",
        "results":all_results[:top_n], "evaluated_style_formations":len(all_results),
        "invalid_combinations":invalid,
        "not_modeled":["Position-style modifiers unless provided from verified source",
                       "Special ability effects, including Ka captain skill",
                       "Weather, home bonus, teamwork/synergy, attitude, match tactics",
                       "Match generator and win probabilities", "Substitutions and future fatigue"],
        "warning":"partial_total is NOT VFL generator's official real strength and cannot alone decide best match strategy"
    }
