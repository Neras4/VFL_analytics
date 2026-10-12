"""RULE_REFERENCE = published example; SYNTHETIC = constructed scenario.
No OBSERVED game data are provided; these do not validate the hidden generator.
"""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from vfl_analytics.arithmetic import round_usefulness
from vfl_analytics.models import Player, StyleKnowledge, PositionPlan
from vfl_analytics.results import CalculationResult, ResultStatus, exact, unknown
from vfl_analytics.rules import (captain_age_factor, captain_bonus, line_chemistry,
    chemistry_for_player, style_effect, baseline_strength, youth_growth, veteran_useful)
from vfl_analytics.season import usefulness, minimum_target_minutes, plan_usefulness
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.cli import run_request
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.transfers import evaluate_purchase
from vfl_analytics.decision import compare_styles
from vfl_analytics.opponent import predict_styles
from test_models import roster, SLOTS


def player(**overrides):
    data = dict(id="a", name="A", positions=("CM",), age=30, strength=100,
                form=100, fatigue=0, nationality="JP", favorite_style="spartak",
                style_known_percent=100)
    data.update(overrides)
    return Player(**data)


@pytest.mark.rule_reference
@pytest.mark.parametrize("raw,expected", [(54.4,54),(54.5,55)])
def test_published_rounding(raw, expected):
    assert round_usefulness(raw) == expected


@pytest.mark.rule_reference
@pytest.mark.parametrize("age,threshold,growth", [(16,20,10),(17,28,9),(18,38,8),
    (19,44,7),(20,48,6),(21,52,5),(22,55,4),(23,57,3)])
def test_published_youth_maximum(age,threshold,growth):
    assert youth_growth(age,threshold) == growth


@pytest.mark.synthetic
@pytest.mark.parametrize("raw,expected", [(0,0),(.49,0),(.5,1),(1.49,1),(1.5,2),
    (19.49,19),(19.5,20),(54.49,54),(55.5,56),(102.5,103),(103.49,103)])
def test_rounding_boundaries(raw, expected):
    assert round_usefulness(raw) == expected


@pytest.mark.synthetic
@pytest.mark.parametrize("played,team,expected", [(93,90,103),(109,200,55),(39,200,20),
    (0,90,0),(199,200,100),(10**20+5*10**17,10**20,101)])
def test_minute_ratio(played, team, expected):
    result = usefulness(played,team)
    assert result.status == ResultStatus.EXACT
    assert result.value == expected
    assert result.unit == "percent"


@pytest.mark.synthetic
def test_growth_veteran_and_zero_denominator():
    assert youth_growth(16,19.5) == 10
    assert veteran_useful(54.5) is True
    assert veteran_useful(54.49) is False
    assert usefulness(0,0).status == ResultStatus.UNKNOWN
    assert usefulness(None,900).value is None
    current = plan_usefulness(16,0,0,900)
    assert current["currently_expected_growth_if_season_ended"] is None
    with pytest.raises(ValueError):
        plan_usefulness(16,0,0,0)


@pytest.mark.synthetic
@pytest.mark.parametrize("bad", [-1,1.5,float("nan"),float("inf"),True])
def test_invalid_minutes(bad):
    with pytest.raises(ValueError):
        usefulness(bad,900)
    with pytest.raises(ValueError):
        minimum_target_minutes(20,bad)


@pytest.mark.synthetic
@pytest.mark.parametrize("threshold,team,target", [(20,4500,878),(55,1800,981),
    (20,1800,351),(2,90,2),(0,90,0),(55,200,109),(100,200,199),(103,90,93)])
def test_minimum_target_is_minimal(threshold,team,target):
    assert minimum_target_minutes(threshold,team) == target
    assert usefulness(target,team).value >= threshold
    if target:
        assert usefulness(target-1,team).value < threshold


@pytest.mark.synthetic
def test_forecast_budget_and_missing_scenario():
    result = plan_usefulness(16,800,4500,0,target_growth=10)
    assert result["minimum_future_player_minutes"] == 78
    assert result["per_player_feasible"] is None
    assert plan_usefulness(16,800,4500,0,10,available_future_player_minutes=78)["per_player_feasible"] is True
    assert plan_usefulness(16,800,4500,0,10,available_future_player_minutes=77)["per_player_feasible"] is False
    result = plan_usefulness(33,109,200,None)
    assert result["veteran_currently_useful"] is True
    assert result["minimum_future_player_minutes"] is None
    assert result["target_minutes_result"]["status"] == "UNKNOWN"
    assert plan_usefulness(16,93,90,0)["current_pct"] == 103
    assert plan_usefulness(16,93,90,0)["minimum_future_player_minutes"] == 0
    assert plan_usefulness(24,10,90,0)["target_minutes_result"]["status"] == "NOT_APPLICABLE"


@pytest.mark.rule_reference
@pytest.mark.parametrize("age,expected", [(16,-.08),(24,0),(25,0),(34,.08)])
def test_captain_boundaries(age,expected):
    assert captain_age_factor(age) == pytest.approx(expected)


@pytest.mark.synthetic
@pytest.mark.parametrize("age", [15,35,100,-1,24.5,24.,True])
def test_captain_invalid_age(age):
    with pytest.raises(ValueError):
        captain_age_factor(age)
    with pytest.raises(ValueError):
        player(age=age)


@pytest.mark.synthetic
@pytest.mark.parametrize("percent,state", [(None,StyleKnowledge.MISSING),(0,StyleKnowledge.UNKNOWN),
    (20,StyleKnowledge.PARTIALLY_STUDIED),(80,StyleKnowledge.PARTIALLY_STUDIED),
    (100,StyleKnowledge.FULLY_KNOWN)])
def test_style_knowledge_and_adapter(percent,state):
    row=dict(playerId=1,name="A",position="CM",age=30,strength=100,favoriteStyle="spartak")
    if percent is not None:
        row["styleKnownPercent"]=percent
    result=adapt_roster({"players":[row]})
    assert result["accepted"] == 1
    p=result["players"][0]
    assert p.style_known_percent == percent
    assert p.style_knowledge == state


@pytest.mark.synthetic
def test_deep_text_does_not_imply_study_and_no_truncation():
    row=dict(playerId=1,name="A",position="CM",age=30,strength=100)
    data={"players":[row],"playerDetails":[{"playerId":1,"info":{"style":"спартаковский"}}]}
    p=adapt_roster(data)["players"][0]
    assert p.favorite_style == "spartak"
    assert p.style_known_percent is None
    assert not p.favorite_style_is_known
    row["styleKnownPercent"]=20.5
    assert adapt_roster(data)["accepted"] == 0
    row["styleKnownPercent"]=100
    row["age"]=30.5
    assert adapt_roster(data)["accepted"] == 0


@pytest.mark.synthetic
@pytest.mark.parametrize("other,expected", [
    ({},(.125,.125)),
    ({"favorite_style":"brazil","nationality":"BR"},(0,0)),
    ({"favorite_style":"bb","nationality":"BR"},(-.05,-.05)),
    ({"favorite_style":None,"style_known_percent":None},(.05,.125)),
    ({"favorite_style":None,"style_known_percent":None,"nationality":"BR"},(-.05,.125)),
    ({"favorite_style":None,"style_known_percent":0,"nationality":"BR"},(-.05,0)),
    ({"favorite_style":"spartak","style_known_percent":20,"nationality":"BR"},(-.05,.025)),
    ({"favorite_style":"bb","nationality":None},(-.05,.05)),
])
def test_chemistry_evidence(other,expected):
    result=line_chemistry(player(),player(id="b",**other))
    if expected[0] == expected[1]:
        assert result.status == ResultStatus.EXACT
        assert result.value == pytest.approx(expected[0])
    else:
        assert result.status == ResultStatus.BOUNDED
        assert result.value is None
        assert (result.lower,result.upper) == pytest.approx(expected)


@pytest.mark.rule_reference
@pytest.mark.parametrize("endpoint", [None,"league"])
def test_zero_endpoints_still_count(endpoint):
    other=None if endpoint is None else player(id="b",is_league_player=True)
    assert line_chemistry(player(),other).value == 0
    assert line_chemistry(other,player()).value == 0
    average,count=chemistry_for_player(player(),[player(id="c"),other])
    assert average.value == .0625
    assert count == 0


@pytest.mark.synthetic
def test_chemistry_interval_average_and_no_lines():
    a=player()
    average,count=chemistry_for_player(a,[None,player(id="b",favorite_style=None)])
    assert (average.lower,average.upper) == (.025,.0625)
    assert count == 1
    assert chemistry_for_player(a,[])[0].status == ResultStatus.NOT_APPLICABLE


@pytest.mark.synthetic
def test_style_uncertainty_not_imputed_into_strength():
    p=player(style_known_percent=None)
    assert style_effect(p,"spartak").value is None
    assert baseline_strength(p,"spartak")[0] is None
    assert baseline_strength(p,"normal")[0] == 100
    p=player(style_known_percent=20,favorite_style_verified=True)
    assert style_effect(p,"spartak").value == 1.005
    assert line_chemistry(player(nationality="BR"),p).value == .025


@pytest.mark.synthetic
def test_lineup_transfer_decision_abstain_on_bounds():
    # All styles verified. Absent nationalities make colliding-line nationality unknown.
    ps=roster()
    ps[1]=player(id="1",positions=("LD",),nationality=None,favorite_style="bb")
    plan=PositionPlan(SLOTS,links=(("LD","CD1"),))
    out=optimize_lineups(ps,[plan],styles=["spartak"])
    ans=out["results"][0]
    assert ans["partial_total"] is None
    assert ans["included_chemistry_bonus"] is None
    assert ans["chemistry_bonus_result"]["status"] == "BOUNDED"
    assert ans["ranking_score_result"]["status"] == "ESTIMATED"
    decision=compare_styles(out["results"],predict_styles([],as_of="2026-10-10"),collision_swing=40)
    assert decision["recommendation"] is None
    assert decision["status"] == "abstain_uncertain_lineup_strength"
    transfer=evaluate_purchase(ps,player(id="new",positions=("CF",)),[plan],styles=["spartak"])
    assert transfer["marginal_partial_strength"] is None
    assert transfer["status"] == "abstain_uncertain_lineup_strength"
    assert out == optimize_lineups(ps,[plan],styles=["spartak"])


@pytest.mark.synthetic
@pytest.mark.parametrize("kwargs", [dict(status="EXACT"),dict(status="BOUNDED",lower=1,upper=0),
    dict(status="UNKNOWN",value=0),dict(status="NOT_APPLICABLE",value=0),
    dict(status="EXACT",value=float("nan")),dict(status="BOUNDED",value=0,lower=0,upper=1)])
def test_invalid_contract(kwargs):
    with pytest.raises(ValueError):
        CalculationResult(**kwargs)


@pytest.mark.synthetic
def test_json_contract_and_cli_nulls():
    assert json.loads(json.dumps(unknown(reason="missing").to_dict()))["value"] is None
    out=run_request(dict(action="usefulness",age=16,played_minutes=39,
                         official_team_minutes=200,future_official_team_minutes=0))
    assert out["current_pct"] == 20
    assert out["currently_expected_growth_if_season_ended"] == 10
    assert json.loads(json.dumps(out))["per_player_feasible"] is None


@pytest.mark.synthetic
@pytest.mark.parametrize("name", ["lineup","opponent","strategy","transfer","usefulness"])
def test_cli_examples(name):
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,"-X","utf8","-m","vfl_analytics.cli",
                           str(root/"examples"/f"{name}.json")],cwd=root,
                          capture_output=True,text=True,encoding="utf8")
    assert result.returncode == 0, result.stderr
    assert isinstance(json.loads(result.stdout),dict)


VECTORS=json.loads((Path(__file__).parent/"fixtures"/"research_vectors.json").read_text(encoding="utf8"))["tests"]


@pytest.mark.synthetic
@pytest.mark.parametrize("vector",VECTORS,ids=[x["id"] for x in VECTORS])
def test_selected_research_vectors(vector):
    assert vector["classification"] == "SYNTHETIC"
    i=vector["inputs"]; e=vector["expected"]; mechanic=vector["mechanic_id"]
    if mechanic == "DEV.USEFULNESS":
        result=usefulness(i["player_minutes"],i["team_minutes"])
        if "percent" in e:
            assert result.value == e["percent"]
            if "veteran_useful" in e:
                assert veteran_useful(result.value) == e["veteran_useful"]
        else:
            assert result.status == ResultStatus.UNKNOWN
            assert result.value is None
    elif mechanic == "DEV.YOUTH.MINUTES":
        r=plan_usefulness(i["age"],i["current_minutes"],i["final_team_minutes"],0,i["target_growth"])
        assert r["target_player_minutes"] == e["required_player_minutes"]
        assert r["minimum_future_player_minutes"] == e["missing_minutes"]
    elif mechanic == "MATCH.CAPTAIN_AGE":
        cap=player(age=i["age"],strength=i["captain_strength"])
        other=i.get("other_strength",2*i.get("on_pitch_mean",100)-cap.strength)
        bonus=captain_bonus(cap,{"a":cap.strength,"b":other})
        if "each_other_add_points" in e:
            assert bonus == pytest.approx(e["each_other_add_points"])
        else:
            assert other+bonus == e["other_component_after"]
    elif mechanic == "MATCH.CHEMISTRY_PLAYER":
        assert chemistry_for_player(player(),[player(id="b"),None])[0].value*100 == e
    else:
        a=player(nationality="JP")
        b=player(id="b",nationality="BR")
        if vector["id"] == "match:chem-directed":
            # Vector explicitly supplies actual same-style truth, independent of study.
            b=player(id="b",nationality="BR",style_known_percent=i["neighbor_studied_pct"],favorite_style_verified=True)
            assert line_chemistry(a,b).value*100 == e["neighbor_to_recipient_pct"]
            assert line_chemistry(b,a).value*100 == e["recipient_to_neighbor_pct"]
        elif vector["id"] == "match:chem-unknown":
            b=player(id="b",nationality="BR",favorite_style=None,style_known_percent=0)
            r=line_chemistry(a,b)
            assert r.value is None
            assert [r.lower*100,r.upper*100] == e["possible_pct"]
        else:
            if i.get("styles_collide"):
                b=player(id="b",nationality="JP" if i.get("same_nationality") else "BR",favorite_style="bb")
            assert line_chemistry(a,b).value*100 == e
