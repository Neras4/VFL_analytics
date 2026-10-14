import json
from dataclasses import replace
import pytest
from vfl_analytics.models import STYLE_NAMES,PositionPlan
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.explain import explain_lineup
from test_models import roster,SLOTS

pytestmark=pytest.mark.synthetic


@pytest.mark.parametrize('mode',['known_components','conservative','pareto'])
def test_all_styles_survive_top_one(mode):
    result=optimize_lineups(roster(),[PositionPlan(SLOTS)],styles=STYLE_NAMES,top_n=1,mode=mode)
    assert len(result['results'])==1
    assert set(result['style_summaries'])==set(STYLE_NAMES)
    for style,summary in result['style_summaries'].items():
        assert summary['plans_considered']==1 and summary['generated_candidates']>0
        assert summary['best_known_proxy']['style']==style
        assert summary['fully_verified_candidates']==0
    assert result['evaluated_style_formations']==7
    json.dumps(result,allow_nan=False)


def test_conservative_point_value_not_lost_to_null_lower():
    result=optimize_lineups(roster(),[PositionPlan(SLOTS)],styles=['normal'],mode='conservative')
    candidate=result['results'][0]
    assert candidate['conservative_score']==candidate['partial_model_range']['value']
    assert candidate['conservative_score'] is not None


def test_explanations_preserve_same_geometry_and_specials():
    players=roster()+[replace(roster()[0],id='keeper2',strength=100,specials=('В4','Р4','Ка3'))]
    plan=PositionPlan(SLOTS);candidate=optimize_lineups(players,[plan],styles=['spartak'])['results'][0]
    explanation=explain_lineup(players,plan,candidate)
    assert explanation==explain_lineup(players,plan,candidate)
    assert explanation['comparisons']
    assert explanation['special_ability_components']['keeper2']
    for comparison in explanation['comparisons']:
        rows=comparison['alternative_lineup']
        assert {r['slot'] for r in rows}==set(SLOTS)
        assert len({r['player_id'] for r in rows})==11
        assert comparison['full_preference_status']=='UNKNOWN'
        expected=sum(r['proxy'] for r in comparison['after'])-sum(r['proxy'] for r in comparison['before'])
        assert comparison['proxy_delta_alternative_minus_selected']==pytest.approx(expected)
        assert comparison['omitted_effects'] and comparison['reason']
    assert any(c['kind']=='same_slot_replacement' and c['before'][0]['assigned_slot']=='GK' for c in explanation['comparisons'])
    assert any(c['kind']=='position_swap' and {r['assigned_slot'] for r in c['before']}=={'AM','CF'} for c in explanation['comparisons'])
    json.dumps(explanation,allow_nan=False)


def test_omitted_specials_do_not_force_artificial_keeper_choice():
    players=roster()+[replace(roster()[0],id='keeper2',strength=10,specials=('В4','Р4','Ка3'))]
    plan=PositionPlan(SLOTS);candidate=optimize_lineups(players,[plan],styles=['normal'])['results'][0]
    assert next(x for x in candidate['lineup'] if x['slot']=='GK')['player_id']=='0'
    e=explain_lineup(players,plan,candidate)
    alt=next(c for c in e['comparisons'] if c['kind']=='same_slot_replacement' and c['after'][0]['player_id']=='keeper2')
    assert alt['proxy_delta_alternative_minus_selected']<0 and alt['full_preference_status']=='UNKNOWN'
