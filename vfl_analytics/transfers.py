"""Candidate's *marginal* effect on the same plan, not naive power/price ranking."""
from __future__ import annotations
from .models import Player, PositionPlan
from .lineup import optimize_lineups


def evaluate_purchase(players: list[Player], candidate: Player, plans: list[PositionPlan],
                      *, price: float | None = None, cash: float | None = None,
                      styles: list[str] | None = None) -> dict:
    if any(p.id == candidate.id for p in players):
        raise ValueError("Candidate already in roster")
    before = optimize_lineups(players,plans,styles,top_n=1)
    after = optimize_lineups(players+[candidate],plans,styles,top_n=1)
    a = after["results"][0]["partial_total"] if after["results"] else None
    b = before["results"][0]["partial_total"] if before["results"] else None
    status = "ok_partial" if (a is not None and b is not None) else "insufficient_roster"
    if before["results"] and after["results"] and (a is None or b is None):
        status = "abstain_uncertain_lineup_strength"
    return {"candidate_id":candidate.id,"status":status,
            "before_score":b,"after_score":a,
            "marginal_partial_strength":round(a-b,3) if a is not None and b is not None else None,
            "price":price,"cash":cash,
            "affordable": None if cash is None or price is None else cash>=price,
            "financial_note":"No ROI/profit forecast without validated price, salary, resale and horizon assumptions",
            "lineup_note":"Scores are partial model comparisons, not true match win-probability gain"}
