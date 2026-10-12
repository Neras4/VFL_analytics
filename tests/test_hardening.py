import json
from dataclasses import replace
from pathlib import Path
import pytest
import jsonschema
from vfl_analytics.models import Player, PositionPlan, MatchObservation
from vfl_analytics.results import CalculationResult, ResultStatus
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.transfers import evaluate_purchase
from vfl_analytics.opponent import predict_styles
from test_models import roster,SLOTS

pytestmark=pytest.mark.synthetic


@pytest.mark.parametrize('field',['strength','form','fatigue','real_strength','value','salary_per_tour','played_minutes'])
@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf'),True,'100',-1])
def test_invalid_player_numbers(field,value):
    with pytest.raises(ValueError):
        replace(roster()[0],**{field:value})


@pytest.mark.parametrize('positions',[('GK','CM'),('CM','CF','CD'),('XYZ',),('DM',),('CM','CM'),('CD','CF'),('LD','RF'),'CM'])
def test_invalid_native_positions(positions):
    with pytest.raises(ValueError):
        replace(roster()[0],positions=positions)


@pytest.mark.parametrize('id',[None,True,1,'',' ','a/b'])
def test_invalid_internal_identity(id):
    with pytest.raises(ValueError):
        replace(roster()[0],id=id)


@pytest.mark.parametrize('specials',[('Ка5',),('foo4',),('Ка1','Ка4'),('Ка',),('Ка4','Ат4','Пк4','И4','Л4'),'Ка4',(3,)])
def test_invalid_specials(specials):
    with pytest.raises(ValueError):
        replace(roster()[0],specials=specials)


@pytest.mark.parametrize('name',['assistant_normal','assistant_deep'])
def test_synthetic_golden_contract(name):
    root=Path(__file__).parent
    data=json.loads((root/'fixtures'/f'{name}.json').read_text(encoding='utf8'))
    schema=json.loads((root/'schemas'/'assistant_snapshot.schema.json').read_text())
    jsonschema.validate(data,schema)
    out=adapt_roster(data)
    assert out['accepted']==1
    p=out['players'][0]
    assert p.id=='101' and p.style_known_percent is None
    assert not p.favorite_style_verified
    if name=='assistant_deep':
        assert (p.form,p.fatigue,p.real_strength)==(112,7,104)
        assert p.salary_per_tour==1200 and p.played_minutes==109
    else:
        assert p.form is None and p.fatigue is None
        e=out['evidence_by_id']['101']
        assert e['selectedStats']['games']==5
        assert e['rosterSeasonStats']['games']==11


def test_duplicate_identity_joins_are_not_last_writer_wins():
    data=json.loads((Path(__file__).parent/'fixtures'/'assistant_deep.json').read_text(encoding='utf8'))
    data['playerDetails'].append({'playerId':'00101','info':{'style':'bb'}})
    out=adapt_roster(data)
    assert out['players'][0].favorite_style is None
    assert any('duplicate_player_details' in x for x in out['issues'])
    data['roster']['players'].append(dict(data['roster']['players'][0]))
    assert adapt_roster(data)['accepted']==1


@pytest.mark.parametrize('id',[True,0,-1,1.5,'abc',None])
def test_invalid_collector_id(id):
    assert adapt_roster({'players':[{'id':id,'name':'A','age':20,'strength':100,'position':'CM'}]})['accepted']==0


def test_present_roster_null_stays_authoritative():
    data=json.loads((Path(__file__).parent/'fixtures'/'assistant_deep.json').read_text(encoding='utf8'))
    data['roster']['players'][0]['form']=None
    assert adapt_roster(data)['players'][0].form is None


def test_unknown_style_and_form_preserve_legal_lineup():
    ps=[replace(p,favorite_style=None,style_known_percent=None) for p in roster()]
    result=optimize_lineups(ps,[PositionPlan(SLOTS)],styles=['spartak'])
    ans=result['results'][0]
    assert len(ans['lineup'])==11
    assert ans['partial_total'] is None
    assert ans['partial_model_range']['status']=='BOUNDED'
    assert ans['ranking_score_result']['status']=='ESTIMATED'
    ps=[replace(p,form=None) for p in ps]
    assert len(optimize_lineups(ps,[PositionPlan(SLOTS)],styles=['spartak'])['results'][0]['lineup'])==11


@pytest.mark.parametrize('strength',[1,50,100,200])
def test_purchase_keeps_incumbent(strength):
    ps=roster()
    new=replace(ps[-1],id='new',strength=strength)
    result=evaluate_purchase(ps,new,[PositionPlan(SLOTS)],styles=['spartak'])
    assert result['incumbent_retained']
    assert result['estimated_search_delta']['value']>=0
    if strength==1:
        assert result['estimated_search_delta']['value']==0


@pytest.mark.parametrize('value',[True,-1,float('nan'),float('inf')])
def test_transfer_prices_and_model_parameters(value):
    with pytest.raises(ValueError):
        evaluate_purchase(roster(),replace(roster()[0],id='new'),[PositionPlan(SLOTS)],price=value)
    with pytest.raises(ValueError):
        predict_styles([],as_of='2026-10-10',half_life_days=value)


@pytest.mark.parametrize('value',['0',True,float('nan'),float('inf')])
def test_result_rejects_invalid_types(value):
    with pytest.raises(ValueError):
        CalculationResult(ResultStatus.EXACT,value=value)


def test_result_json_schema_and_fixture_integrity():
    root=Path(__file__).parent
    schema=json.loads((root/'schemas'/'result.schema.json').read_text())
    for value in [CalculationResult(ResultStatus.EXACT,value=1),CalculationResult(ResultStatus.BOUNDED,lower=0,upper=1),
                  CalculationResult(ResultStatus.UNKNOWN),CalculationResult(ResultStatus.NOT_APPLICABLE),
                  CalculationResult(ResultStatus.ESTIMATED,value=2)]:
        jsonschema.validate(value.to_dict(),schema)
    for path in (root/'fixtures').glob('*.json'):
        json.loads(path.read_text(encoding='utf8'))
