import json
import copy
from dataclasses import replace
from pathlib import Path
import pytest,jsonschema
from vfl_analytics.results import ResultStatus
from vfl_analytics.evaluation import evaluate_player,lineup_captain_components
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.models import STYLE_NAMES,PositionPlan
from vfl_analytics.rules import collision
from vfl_analytics.rule_data import load_rule_data
from vfl_analytics.abilities import ability_lookup
from vfl_analytics.cli import run_request
from test_models import roster,SLOTS

pytestmark=pytest.mark.synthetic


@pytest.mark.parametrize('ours',STYLE_NAMES)
@pytest.mark.parametrize('theirs',STYLE_NAMES)
def test_entire_collision_matrix(ours,theirs):
    matrix=load_rule_data('style_positions.json')['style_collision']['matrix']
    assert collision(ours,theirs)==matrix[STYLE_NAMES.index(ours)][STYLE_NAMES.index(theirs)]
    assert collision(ours,theirs)==-collision(theirs,ours)
    if ours==theirs or 'normal' in (ours,theirs): assert collision(ours,theirs)==0


def test_unknown_collision_inputs_rejected():
    with pytest.raises(ValueError): collision(None,None)


def test_player_components_weather_uses_actual_favorite_not_team_style():
    p=replace(roster()[7],strength=350,favorite_style='spartak',specials=('Пк4','У4'))
    report=evaluate_player(p,'CM','bb',weather={'weather':'HOT','temperature_c':29}).to_dict()
    assert report['components']['weather']['value']==177  # solar player; rain team would give152
    assert report['components']['favorite_style']['value']==.99
    assert report['total_strength']['status']=='UNKNOWN'
    assert report['partial_estimate']['status']=='ESTIMATED'
    assert report['components']['special_abilities'][1]['effects'][0]['scope']=='moment_specific'
    unknown=replace(p,favorite_style=None,style_known_percent=None)
    report=evaluate_player(unknown,'CM','bb',weather={'weather':'HOT','temperature_c':29}).to_dict()
    assert report['components']['weather']['lower']==152
    assert report['components']['weather']['upper']==177
    assert report['components']['weather']['value'] is None


@pytest.mark.parametrize('mode',['known_components','conservative','pareto'])
def test_ranking_modes_determinism_and_incumbent(mode):
    ps=[replace(p,favorite_style=None,style_known_percent=None) for p in roster()]
    plan=PositionPlan(SLOTS,tactical_permissions={'DM':True,'AM':True})
    before=optimize_lineups(ps,[plan],styles=['spartak'],top_n=30,mode=mode)
    assert before['recommendation'] is None
    assert all(x['partial_total'] is None for x in before['results'])
    assert before==optimize_lineups(ps,[plan],styles=['spartak'],top_n=30,mode=mode)
    after=optimize_lineups(ps+[replace(ps[-1],id='new',strength=1)],[plan],styles=['spartak'],top_n=30,
                           mode=mode,incumbents=before['results'])
    assert all(x['incumbents_retained'] for x in after['results'])
    if mode=='conservative':
        assert after['results'][0]['conservative_score']>=before['results'][0]['conservative_score']
    if mode=='known_components':
        assert after['results'][0]['ranking_score']>=before['results'][0]['ranking_score']


def test_real_position_force_context_is_explicit_and_captain_preserved():
    ps=roster(); ps[0]=replace(ps[0],age=16,specials=('Ка4',),real_strength=999)
    mapping={slot:p for slot,p in zip(SLOTS,ps)}
    assert lineup_captain_components(mapping)['captain_id'] is None
    forces={slot:{p.id:100} for slot,p in mapping.items()}
    out=lineup_captain_components(mapping,real_position_strengths=forces,strength_basis_verified=True)
    assert out['captain_id']=='0'
    assert out['best_isolated_delta']['value']==120
    assert out['best_isolated_delta']['status']=='EXACT'


def test_schemas_and_source_evidence_are_offline_and_valid():
    root=Path(__file__).parent
    schema=json.loads((root/'schemas'/'rule_data.schema.json').read_text())
    for name in ('core.json','abilities.json','style_positions.json','weather.json.gz'):
        jsonschema.validate(load_rule_data(name),schema)
    report=json.loads((root.parent/'docs'/'source_verification.json').read_text(encoding='utf8'))
    assert len(report['ability_verification'])==21
    assert sum(x['published_numeric_cells_verified'] for x in report['ability_verification'])==385


def test_expanded_cli_contracts():
    assert run_request({'action':'validate_rules'})['status']=='valid'
    assert run_request({'action':'weather','player_style':'spartak','nominal_strength':350,'weather':'HOT','temperature_c':29})['value']==177
    assert run_request({'action':'ability','code':'Пк','level':4,'context':{'team_style':'spartak'}})['effects'][0]['result']['value']==.4
    assert run_request({'action':'position','native_positions':['CD','CM'],'slot':'DM','team_style':'spartak'})['modifier']['value']==1.05
    assert run_request({'action':'captain','age':34,'ka_level':4,'captain_id':'a','on_pitch_strengths':{'a':100,'b':100}})['status']=='UNKNOWN'


@pytest.mark.parametrize('code,kind,param,index,expected',[('Тр','injury_severity_given_injury','competitive_levels0to4',0,.9),
    ('Тр','injury_severity_given_injury','friendly_levels0to4',1,.05)])
def test_injury_vectors_are_conditional_probabilities(code,kind,param,index,expected):
    out=ability_lookup(code,4,kind,param,index=index)
    assert out.value==expected and out.unit=='conditional_probability'


def test_unobserved_specials_are_not_a_confirmed_empty_list():
    p=replace(roster()[7],specials_known=False)
    result=evaluate_player(p,'CM','normal').to_dict()
    assert result['components']['special_abilities'][0]['result']['status']=='UNKNOWN'
