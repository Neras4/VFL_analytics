import json
from copy import deepcopy
from dataclasses import replace
import pytest
from vfl_analytics.cli import run_request, plans_from
from vfl_analytics.models import PositionPlan
from vfl_analytics.local_validation import analyze_team, scenario_plans, validate_directory
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.evaluation import evaluate_player
from vfl_analytics.positions import position_modifier
from vfl_analytics.abilities import captain_coefficient
from test_observed_contracts import fixture
from test_models import SLOTS


@pytest.mark.observed
@pytest.mark.integration
@pytest.mark.parametrize('name',['own','opponent'])
def test_observed_component_pipeline(name):
    report=analyze_team([fixture(name+'_deep'),fixture(name+'_normal')],lineups=False)
    assert report['join']['accepted']==3
    assert len(report['evaluations'])==9
    json.dumps(report,allow_nan=False)
    for evaluation in report['evaluations']:
        c=evaluation['components']
        assert c['captain']['status']==c['chemistry']['status']==c['cohesion']['status']=='UNKNOWN'
        assert c['weather']['status']=='UNKNOWN'
        assert evaluation['total_strength']['value'] is None
        if name=='opponent':
            assert c['physical_form']['value'] is c['fatigue']['value'] is None
    assert report['weather_scenario']['classification']=='SYNTHETIC_SCENARIO'


@pytest.mark.synthetic
@pytest.mark.integration
@pytest.mark.parametrize('mode',['known_components','conservative','pareto'])
def test_json_adapter_rules_optimizer_roundtrip(mode):
    # Three real structural examples expanded to an artificial 11-player roster.
    snapshot=fixture('own_deep');source=deepcopy(snapshot['roster']['players'][1])
    snapshot['roster']['players']=[snapshot['roster']['players'][0]]
    for i,position in enumerate(['LD','CD','CD','RD','LM','CM','CM','RM','CF','CF']):
        snapshot['roster']['players'].append({**source,'id':str(400+i),'position':position,'specials':[]})
    adapted=run_request({'action':'adapt','snapshot':snapshot})
    players=[{k:v for k,v in p.items() if k!='style_knowledge'} for p in adapted['players']]
    request={'action':'lineup','players':players,'plans':[{'slots':list(scenario_plans()[0].slots)}],
             'styles':['spartak'],'mode':mode,'top_n':3}
    result=run_request(json.loads(json.dumps(request)))
    assert result==run_request(request)
    assert result['recommendation'] is None
    for candidate in result['results']:
        assert len(candidate['lineup'])==len({p['player_id'] for p in candidate['lineup']})==11
        assert sum(p['slot']=='GK' for p in candidate['lineup'])==1
        assert candidate['lineup_eligibility']['status']=='UNKNOWN'
        assert candidate['partial_total'] is None
        assert candidate['captain_component']['best_isolated_delta']['status']=='UNKNOWN'
    json.dumps(result,allow_nan=False)


@pytest.mark.rule_reference
@pytest.mark.parametrize('profile,slot,expected',[(('CD','CM'),'DM',1.05),(('CM','CF'),'AM',1.05),(('LM','LF'),'LW',1.05)])
def test_reference_special_positions_remain_separate_from_legality(profile,slot,expected):
    # page159 v2.1 positional cells, not a proof of complete formation legality.
    assert position_modifier(profile,slot).value==expected


@pytest.mark.observed
def test_observed_captain_coefficient_does_not_infer_real_base():
    players=adapt_roster(fixture('own_deep'))['players']
    for player in players:
        assert captain_coefficient(player.age,0).value is not None
        report=evaluate_player(player,player.positions[0],'spartak').to_dict()
        assert report['components']['captain']['value'] is None
        assert report['components']['special_abilities']


@pytest.mark.synthetic
@pytest.mark.regression
@pytest.mark.parametrize('links',[None,[None],['GK'],[('GK','missing')],[('GK','GK')],[('GK','LD'),('LD','GK')],[(None,'GK')],[(('GK',),'LD')]])
def test_bad_links_raise_valueerror(links):
    with pytest.raises(ValueError):PositionPlan(SLOTS,links=links)


@pytest.mark.synthetic
def test_chemistry_links_are_undirected_and_unique():
    assert PositionPlan(SLOTS,links=[('GK','LD')]).links==[('GK','LD')]
    assert PositionPlan(SLOTS,links=[('LD','GK')]).links==[('LD','GK')]


@pytest.mark.synthetic
@pytest.mark.parametrize('change',['source','rule_version','verification_status','unit'])
def test_external_factor_metadata_required_fields(change):
    metadata={'source':'research scenario','rule_version':'scenario-v1','verification_status':'UNVERIFIED','unit':'multiplier'}
    metadata.pop(change)
    with pytest.raises(ValueError):PositionPlan(SLOTS,{'spartak':{'DM':1.1}},style_position_provenance={'spartak':metadata})


@pytest.mark.synthetic
def test_external_scenario_origin_survives_cli():
    metadata={'source':'local research scenario','rule_version':'hypothesis-v1','verification_status':'UNVERIFIED','unit':'multiplier'}
    plan=plans_from([{'slots':SLOTS,'style_position_multipliers':{'Спартак':{'DM':1.1}},
                     'style_position_provenance':{'Спартак':metadata}}])[0]
    assert plan.style_position_multipliers['spartak']['DM']==1.1
    assert plan.style_position_provenance['spartak']==metadata
    from test_models import roster
    from vfl_analytics.lineup import optimize_lineups
    candidate=optimize_lineups(roster(),[plan],styles=['spartak'])['results'][0]
    assert candidate['external_position_factors']['status']=='ESTIMATED'
    assert candidate['external_position_factors']['provenance']==metadata


@pytest.mark.synthetic
@pytest.mark.regression
@pytest.mark.parametrize('name',['lineup','strategy','usefulness','transfer','evaluate_player'])
def test_existing_cli_examples(name):
    from pathlib import Path
    request=json.loads((Path(__file__).parents[1]/'examples'/(name+'.json')).read_text(encoding='utf8'))
    json.dumps(run_request(request),allow_nan=False)


@pytest.mark.synthetic
def test_malformed_optional_season_stats_does_not_lose_roster():
    d=fixture('own_deep');d['rosterSeasonStats']=[]
    result=adapt_roster(d)
    assert result['accepted']==3 and result['error_count']==1


@pytest.mark.synthetic
def test_ambiguous_season_stats_never_last_writer_wins():
    d=fixture('own_deep');d['rosterSeasonStats']['players']*=2
    result=adapt_roster(d)
    assert result['accepted']==3
    assert all(e['rosterSeasonStats'] is None for e in result['evidence_by_id'].values())


@pytest.mark.synthetic
def test_private_audit_requires_local_output():
    with pytest.raises(ValueError,match='local_data'):
        validate_directory('.', 'docs/raw-output-forbidden')


@pytest.mark.synthetic
def test_null_specials_mean_unknown_not_known_empty():
    snapshot=fixture('own_deep');snapshot['team']=None
    snapshot['roster']['players'][0]['specials']=None
    player=adapt_roster(snapshot)['players'][0]
    assert not player.specials_known and player.specials==()
    report=evaluate_player(player,player.positions[0],'normal').to_dict()
    assert report['components']['special_abilities'][0]['result']['status']=='UNKNOWN'


@pytest.mark.observed
@pytest.mark.parametrize('name',['market_50','market_38'])
def test_observed_multistyle_does_not_collapse_to_one_style(name):
    from vfl_analytics.market_adapter import adapt_market_snapshot
    result=adapt_market_snapshot(fixture(name))
    assert len(result['rows'][1]['possible_styles'])>1
    assert result['rows'][1]['favorite_style_verified'] is False
