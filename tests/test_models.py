import pytest
pytestmark = pytest.mark.synthetic
from vfl_analytics.models import Player,PositionPlan,MatchObservation
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.opponent import predict_styles,collision_exposure
from vfl_analytics.season import plan_usefulness
from vfl_analytics.transfers import evaluate_purchase
from vfl_analytics.adapters import adapt_roster

SLOTS = ('GK','LD','CD1','CD2','RD','LM','DM','CM','RM','AM','CF')

def roster():
    positions=('GK','LD','CD','CD','RD','LM','DM','CM','RM','AM','CF','CF')
    ps=[]
    for i,pos in enumerate(positions):
        ps.append(Player(str(i),f'P{i}',(pos,),28,70+i,10,110,
                         favorite_style='spartak',style_known_percent=100))
    return ps


def test_lineup_valid_and_unique():
    output=optimize_lineups(roster(),[PositionPlan(SLOTS)],styles=['spartak'],top_n=1)
    assert output['status']=='partial_model'
    ans=output['results'][0]
    assert len(ans['lineup'])==11
    assert len({x['player_id'] for x in ans['lineup']})==11
    assert ans['lineup'][-1]['player_id']=='11'
    assert 'position_style_table_missing: position/style effects omitted' in ans['warnings']
    assert ans['partial_total']>0


def test_invalid_lineup_no_imputed_positions():
    out=optimize_lineups(roster()[:-3],[PositionPlan(SLOTS)],styles=['spartak'])
    assert out['status']=='no_valid_lineup'


def test_transfer_is_marginal_not_roster_sum():
    players=roster()
    cand=Player('new','Forward',('CF',),25,150,0,100,favorite_style='spartak',style_known_percent=100)
    out=evaluate_purchase(players,cand,[PositionPlan(SLOTS)],styles=['spartak'],price=500,cash=450)
    assert out['marginal_partial_strength']>0
    assert out['affordable'] is False


def test_opponent_prediction_future_leak_excluded():
    obs=[MatchObservation('bb','2026-10-01'),MatchObservation('bb','2026-10-02'),
         MatchObservation('tiki','2026-10-15')]
    out=predict_styles(obs,as_of='2026-10-10')
    assert out['matches_used']==2
    assert sum(out['probabilities'].values())==pytest.approx(1,abs=0.00006)
    risk=collision_exposure(out['probabilities'])
    assert risk['brazil']['p_win_collision']>0
    assert risk['spartak']['p_lose_collision']>0
    assert out['status']=='limited_evidence'


def test_usefulness_projection_denominator_increases():
    p=plan_usefulness(16,100,900,900,target_growth=10)
    assert p['minimum_future_player_minutes']==251
    assert p['per_player_feasible'] is None  # No player availability budget supplied.
    old=plan_usefulness(33,50,900,900)
    assert old['minimum_future_player_minutes']==931
    assert old['per_player_feasible'] is None


def test_adapter_unknown_is_not_zero():
    data={'roster':{'players':[{'playerId':51,'name':'A','age':21,'strength':71,
           'position':'LD/LM','fatigue':'?','form':'112%'}]}}
    result=adapt_roster(data)
    assert result['accepted']==1
    assert result['players'][0].fatigue is None
    assert result['players'][0].form==112
    assert 'row[0]:unknown_form_or_fatigue' in result['issues']


def test_decision_abstains_without_fabricated_collision_magnitude():
    from vfl_analytics.decision import compare_styles
    out=predict_styles([MatchObservation('bb','2026-10-01')],as_of='2026-10-10')
    a=[{'style':'spartak','partial_total':1300},{'style':'brazil','partial_total':1280}]
    abstain=compare_styles(a,out,collision_swing=None)
    assert abstain['recommendation'] is None
    assert abstain['status']=='abstain_collision_magnitude_unknown'
    assumed=compare_styles(a,out,collision_swing=40,risk_weight=0.5,samples=400,seed=42)
    assert assumed['status']=='scenario_only'
    assert len(assumed['options'])==2
    assert assumed['parameters']['assumed_collision_swing_strength_units']==40
