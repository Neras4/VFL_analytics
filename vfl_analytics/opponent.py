"""Explicitly approximate, recency-weighted Dirichlet-style posterior.
This is NOT a calibrated win predictor and fractional weights are generalized Bayes.
"""
from __future__ import annotations
from dataclasses import asdict
from datetime import date
from math import exp, log
from scipy.stats import beta
from .models import STYLE_NAMES, MatchObservation
from .rules import collision
from .validation import number


def predict_styles(history: list[MatchObservation], *, as_of: str,
                   home: bool | None = None, strength_ratio: float | None = None,
                   half_life_days: float = 90, prior_strength: float = 7) -> dict:
    number(half_life_days,'half_life_days',positive=True)
    number(prior_strength,'prior_strength',positive=True)
    if strength_ratio is not None:
        number(strength_ratio,'strength_ratio',positive=True)
    if home is not None and not isinstance(home,bool):
        raise ValueError('home must be boolean or null')
    target = date.fromisoformat(as_of)
    categories = STYLE_NAMES
    alpha = {s: prior_strength/len(categories) for s in categories}
    counts = {s: 0 for s in categories}
    total_weight = 0.0
    used = 0
    for game in history:
        played = date.fromisoformat(game.date)
        if played >= target:
            continue  # never learn from target/future games
        days = (target - played).days
        weight = 0.5**(days / half_life_days)
        if home is not None and game.home is not None and game.home != home:
            weight *= .7  # EXPLICIT uncalibrated similarity heuristic
        if strength_ratio is not None and game.opponent_strength_ratio is not None:
            weight *= exp(-abs(log(game.opponent_strength_ratio / strength_ratio)))
        alpha[game.style] += weight
        counts[game.style] += 1
        total_weight += weight
        used += 1
    a0 = sum(alpha.values())
    probabilities = {s: alpha[s]/a0 for s in categories}
    intervals = {s: [round(float(beta.ppf(.05, alpha[s], a0-alpha[s])), 4),
                     round(float(beta.ppf(.95, alpha[s], a0-alpha[s])), 4)] for s in categories}
    return {"as_of": as_of, "matches_used": used,
            "effective_weighted_matches": round(total_weight, 3),
            "observed_counts": counts,
            "posterior_alpha": {s:round(alpha[s],6) for s in categories},
            "probabilities": {s: round(v, 5) for s, v in probabilities.items()},
            "interval90_approx": intervals,
            "method": "recency_weighted_dirichlet_generalized_posterior",
            "status": "limited_evidence" if total_weight < 5 else "estimated_not_calibrated",
            "limitations": ["Uniform pseudocount prior; posterior is not a calibrated frequency guarantee",
                            "Home/strength similarity weights are research assumptions, not VFL rules",
                            "Missing tactical context (injuries, manager substitution, objectives) is not modeled"]}


def collision_exposure(style_probabilities: dict[str, float]) -> dict:
    """Known direction, uncertain style. No made-up collision strength bonus."""
    result = {}
    for ours in STYLE_NAMES:
        pos = sum(p for theirs,p in style_probabilities.items() if collision(ours,theirs)==1)
        neg = sum(p for theirs,p in style_probabilities.items() if collision(ours,theirs)==-1)
        result[ours] = {"p_win_collision": round(pos,5),
                        "p_lose_collision": round(neg,5),
                        "p_neutral": round(max(0.0,1-pos-neg),5)}
    return result
