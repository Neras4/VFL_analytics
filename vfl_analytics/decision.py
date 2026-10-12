"""Probabilistic scenario decision support, NOT match result prediction.
The collision bonus magnitude is NOT in scraped plaintext rules; requires
external calibration. No recommended style without an explicit assumption.
"""
from __future__ import annotations
import numpy as np
from .models import STYLE_NAMES
from .rules import collision
from .validation import number


def compare_styles(lineups: list[dict], style_prediction: dict,
                   collision_swing: float | None = None,
                   risk_weight: float = 0.0, samples: int = 2000,
                   seed: int = 79) -> dict:
    """Utility units are partial_strength units; collision_swing is an assumed
    +/- additive effect on score (NOT %). Null => report exposure, abstain.
    With risk_weight > 0 the proxy score is posterior mean - risk_weight*SD.
    """
    number(risk_weight,'risk_weight',minimum=0)
    number(samples,'samples',minimum=100,maximum=100000,integer=True)
    number(seed,'seed',minimum=0,integer=True)
    if collision_swing is not None:
        number(collision_swing,'collision_swing',minimum=0)
    if not lineups:
        return {"status":"no_lineups","options":[],"recommendation":None}
    if any(x.get("partial_total") is None for x in lineups):
        return {"status":"abstain_uncertain_lineup_strength","options":lineups,
                "recommendation":None,
                "note":"Chemistry bounds cannot be substituted with a point strength"}
    probs = style_prediction["probabilities"]
    alpha = style_prediction["posterior_alpha"]
    cats = list(STYLE_NAMES)
    draws = np.random.default_rng(seed).dirichlet([alpha[s] for s in cats], size=samples)
    options = []
    for opt in lineups:
        s = opt["style"]
        base = float(opt["partial_total"])
        vector = np.array([collision(s,other) for other in cats],dtype=float)
        expected_direction = float(sum(probs[t]*collision(s,t) for t in cats))
        exposure = {"p_win":round(sum(probs[t] for t in cats if collision(s,t)==1),4),
                    "p_loss":round(sum(probs[t] for t in cats if collision(s,t)==-1),4)}
        result = {"style":s,"slots":opt.get("slots"),"partial_base_strength":base,
                  "collision_exposure":exposure,"expected_collision_direction":round(expected_direction,4),
                  "notes":opt.get("warnings",[])}
        if collision_swing is not None:
            utility_draws = base + collision_swing * (draws @ vector)
            result.update({"scenario_expected_score":round(float(np.mean(utility_draws)),3),
                           "scenario_p05":round(float(np.percentile(utility_draws,5)),3),
                           "scenario_p95":round(float(np.percentile(utility_draws,95)),3),
                           "scenario_std":round(float(np.std(utility_draws)),3),
                           "risk_adjusted_score":round(float(np.mean(utility_draws) - risk_weight*np.std(utility_draws)),3)})
        options.append(result)
    if collision_swing is None:
        return {"status":"abstain_collision_magnitude_unknown","recommendation":None,
                "options":options,
                "note":"No winner: relative position-style factors and actual collision bonus are not modeled. Do not rank on a made-up value."}
    options.sort(key=lambda x:x["risk_adjusted_score"],reverse=True)
    return {"status":"scenario_only","recommendation":options[0]["style"],
            "options":options,
            "parameters":{"assumed_collision_swing_strength_units":collision_swing,
                          "risk_weight":risk_weight,"seed":seed,"samples":samples},
            "note":"This is a sensitivity result under a user-specified assumed collision magnitude, not a calibrated win-probability forecast."}
