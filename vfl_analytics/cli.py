"""JSON-in JSON-out local interface; MCP adapter can later wrap run_request."""
from __future__ import annotations
import argparse,json,sys
from dataclasses import asdict
from .models import Player, PositionPlan, MatchObservation
from .opponent import predict_styles, collision_exposure
from .lineup import optimize_lineups
from .rules import collision, youth_growth, defense_choice
from .season import plan_usefulness
from .transfers import evaluate_purchase
from .adapters import adapt_roster
from .decision import compare_styles


def make_players(rows):
    result=[]
    for r in rows:
        rec=dict(r)
        rec["positions"] = tuple(rec["positions"])
        if "specials" in rec: rec["specials"]=tuple(rec["specials"])
        result.append(Player(**rec))
    return result


def plans_from(rows):
    return [PositionPlan(tuple(x["slots"]),x.get("style_position_multipliers",{}),
                         tuple(tuple(y) for y in x.get("links",[])),x.get('defense_formation')) for x in rows]


def run_request(obj:dict)->dict:
    op = obj.get("action")
    if op=="opponent":
        dist = predict_styles([MatchObservation(**x) for x in obj["history"]],
                              as_of=obj["as_of"],home=obj.get("home"),
                              strength_ratio=obj.get("strength_ratio"),
                              half_life_days=obj.get("half_life_days",90),
                              prior_strength=obj.get("prior_strength",7))
        return {"prediction":dist,"collision_exposure":collision_exposure(dist["probabilities"])}
    if op=="lineup":
        return optimize_lineups(make_players(obj["players"]),plans_from(obj["plans"]),
                                styles=obj.get("styles"),top_n=obj.get("top_n",3),mode=obj.get('mode','known_components'))
    if op=="strategy":
        pred=predict_styles([MatchObservation(**x) for x in obj["history"]],
            as_of=obj["as_of"],home=obj.get("home"),strength_ratio=obj.get("strength_ratio"))
        opts=optimize_lineups(make_players(obj["players"]),plans_from(obj["plans"]),
                              styles=obj.get("styles"),top_n=100)
        return {"opponent":pred,"lineups":opts,"decision":compare_styles(opts["results"],pred,
            collision_swing=obj.get("collision_swing"),risk_weight=obj.get("risk_weight",0),
            seed=obj.get("seed",79))}
    if op=="transfer":
        return evaluate_purchase(make_players(obj["players"]),
                                 make_players([obj["candidate"]])[0],
                                 plans_from(obj["plans"]),price=obj.get("price"),
                                 cash=obj.get("cash"),styles=obj.get("styles"))
    if op=="usefulness":
        return plan_usefulness(obj["age"],obj["played_minutes"],
                               obj["official_team_minutes"],obj["future_official_team_minutes"],
                               obj.get("target_growth"),
                               available_future_player_minutes=obj.get("available_future_player_minutes"))
    if op=="adapt":
        r=adapt_roster(obj["snapshot"])
        return {**r,"players":[{**asdict(x),"style_knowledge":x.style_knowledge.value} for x in r["players"]]}
    if op=="collision":
        return {"direction":collision(obj["our_style"],obj["their_style"])}
    raise ValueError("Unknown action; use opponent,lineup,strategy,transfer,usefulness,adapt,collision")


def main():
    p=argparse.ArgumentParser(description="VFL analytical engine JSON-in JSON-out")
    p.add_argument("input",help="JSON input file")
    args=p.parse_args()
    with open(args.input,encoding="utf8") as f:
        obj=json.load(f)
    try:
        result=run_request(obj)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,KeyError,TypeError) as e:
        print(json.dumps({"error":type(e).__name__,"message":str(e)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)

if __name__=="__main__": main()
