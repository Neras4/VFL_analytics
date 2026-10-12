"""Candidate's *marginal* effect on the same plan, not naive power/price ranking."""
from __future__ import annotations
from .models import Player, PositionPlan
from .lineup import optimize_lineups
from .validation import number
from .results import CalculationResult,ResultStatus
from .results import unknown


def evaluate_purchase(players: list[Player], candidate: Player, plans: list[PositionPlan],
                      *, price: float | None = None, cash: float | None = None,
                      styles: list[str] | None = None,context: dict | None = None) -> dict:
    if any(p.id == candidate.id for p in players):
        raise ValueError("Candidate already in roster")
    for name,value in [('price',price),('cash',cash)]:
        if value is not None:
            number(value,name,minimum=0)
    before = optimize_lineups(players,plans,styles,top_n=224,context=context)
    after = optimize_lineups(players+[candidate],plans,styles,top_n=1,incumbents=before['results'],context=context)
    a = after["results"][0]["partial_total"] if after["results"] else None
    b = before["results"][0]["partial_total"] if before["results"] else None
    status = "ok_partial" if (a is not None and b is not None) else "insufficient_roster"
    if before["results"] and after["results"] and (a is None or b is None):
        status = "abstain_uncertain_lineup_strength"
    search_delta=None
    if before['results'] and after['results']:
        search_delta=after['results'][0]['ranking_score']-before['results'][0]['ranking_score']
        if search_delta < -1e-8:
            raise RuntimeError('Incumbent invariant violated for identical search objective')
        search_delta=max(0.,search_delta)
    return {"candidate_id":candidate.id,"status":status,
            'marginal_partial_strength_result':unknown(unit='partial_strength_units',reason='Point delta unavailable').to_dict() if a is None or b is None else
                CalculationResult(ResultStatus.ESTIMATED,value=a-b,unit='partial_strength_units',reason='Same conditional partial-model objective; full modifiers and economic ROI unresolved').to_dict(),
            'economic_value':unknown(unit='currency',reason='Salary, resale, commissions and horizon not modeled').to_dict(),
            "incumbent_retained":any(x.get('incumbents_retained',0)>0 for x in after['results']),
            "estimated_search_delta":None if search_delta is None else CalculationResult(ResultStatus.ESTIMATED,
                value=search_delta,unit='partial_strength_units',reason='Same explicit search proxy, incumbent preserved; not economic ROI or true force gain').to_dict(),
            "before_score":b,"after_score":a,
            "marginal_partial_strength":round(a-b,3) if a is not None and b is not None else None,
            "price":price,"cash":cash,
            "affordable": None if cash is None or price is None else cash>=price,
            "financial_note":"No ROI/profit forecast without validated price, salary, resale and horizon assumptions",
            "lineup_note":"Scores are partial model comparisons, not true match win-probability gain"}
