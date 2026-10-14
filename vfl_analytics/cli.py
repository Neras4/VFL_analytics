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
from .snapshots import merge_team_snapshots
from .market_adapter import adapt_market_snapshot
from .decision import compare_styles
from .evaluation import evaluate_player
from .positions import position_modifier,style_position_category
from .weather import weather_strength
from .cohesion import cohesion_bonus
from .abilities import ability_components,ability_lookup,catalog,captain_contribution
from .rule_data import validate_all


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
                         tuple(tuple(y) for y in x.get("links",[])),x.get('defense_formation'),
                         tuple(x['formation_base_slots']) if x.get('formation_base_slots') is not None else None,
                         x.get('tactical_permissions',{}),x.get('style_position_provenance',{})) for x in rows]


def run_request(obj:dict)->dict:
    if not isinstance(obj,dict):
        raise ValueError('CLI request must be an object')
    op = obj.get("action")
    if op=='adapt_market':
        return adapt_market_snapshot(obj['snapshot'])
    if op=='merge_snapshots':
        merged=merge_team_snapshots(obj['snapshots'])
        adapted=adapt_roster(merged['snapshot'])
        return {**merged,'adapted':{**adapted,'players':[asdict(p) for p in adapted['players']]}}
    if op=='validate_rules':
        return validate_all()
    if op=='catalog':
        return {'abilities':catalog(),'combined_strength':None,'note':'Distinct phases and bases; no total-force sum'}
    if op=='position':
        return {'modifier':position_modifier(obj['native_positions'],obj['slot']).to_dict(),
                'style_category':style_position_category(obj['team_style'],obj['slot'],obj.get('defense_formation'))}
    if op=='weather':
        return weather_strength(obj['player_style'],obj['nominal_strength'],obj['weather'],obj['temperature_c']).to_dict()
    if op=='ability':
        if obj.get('parameter') is not None:
            return ability_lookup(obj['code'],obj['level'],obj['effect_kind'],obj['parameter'],**obj.get('selectors',{})).to_dict()
        return ability_components(obj['code'],obj['level'],**obj.get('context',{}))
    if op=='captain':
        return captain_contribution(obj['age'],obj.get('ka_level',0),obj['captain_id'],obj.get('on_pitch_strengths'),
            strength_basis_verified=obj.get('strength_basis_verified',False),unresolved_modifiers=obj.get('unresolved_modifiers',False)).to_dict()
    if op=='cohesion':
        return cohesion_bonus(obj.get('current_player_ids'),obj.get('history'),history_complete=obj.get('history_complete',False)).to_dict()
    if op=='evaluate_player':
        return evaluate_player(make_players([obj['player']])[0],obj['slot'],obj['team_style'],**obj.get('context',{})).to_dict()
    if op=="opponent":
        dist = predict_styles([MatchObservation(**x) for x in obj["history"]],
                              as_of=obj["as_of"],home=obj.get("home"),
                              strength_ratio=obj.get("strength_ratio"),
                              half_life_days=obj.get("half_life_days",90),
                              prior_strength=obj.get("prior_strength",7))
        return {"prediction":dist,"collision_exposure":collision_exposure(dist["probabilities"])}
    if op=="lineup":
        return optimize_lineups(make_players(obj["players"]),plans_from(obj["plans"]),
                                styles=obj.get("styles"),top_n=obj.get("top_n",3),mode=obj.get('mode','known_components'),context=obj.get('context'))
    if op=="strategy":
        pred=predict_styles([MatchObservation(**x) for x in obj["history"]],
            as_of=obj["as_of"],home=obj.get("home"),strength_ratio=obj.get("strength_ratio"))
        opts=optimize_lineups(make_players(obj["players"]),plans_from(obj["plans"]),
                              styles=obj.get("styles"),top_n=100,mode=obj.get('mode','known_components'),context=obj.get('context'))
        return {"opponent":pred,"lineups":opts,"decision":compare_styles(opts["results"],pred,
            collision_swing=obj.get("collision_swing"),risk_weight=obj.get("risk_weight",0),
            seed=obj.get("seed",79))}
    if op=="transfer":
        return evaluate_purchase(make_players(obj["players"]),
                                 make_players([obj["candidate"]])[0],
                                 plans_from(obj["plans"]),price=obj.get("price"),
                                 cash=obj.get("cash"),styles=obj.get("styles"),context=obj.get('context'))
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
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):
            stream.reconfigure(encoding='utf8')
    p=argparse.ArgumentParser(description="VFL analytical engine JSON-in JSON-out")
    p.add_argument("input",help="JSON input file")
    args=p.parse_args()
    try:
        def reject_constant(value):
            raise ValueError('Nonfinite JSON number: '+value)
        with open(args.input,encoding='utf8') as f:
            obj=json.load(f,parse_constant=reject_constant)
        result=run_request(obj)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(json.dumps({"error":type(e).__name__,"message":str(e)},ensure_ascii=False),file=sys.stderr)
        raise SystemExit(2)

if __name__=="__main__": main()
