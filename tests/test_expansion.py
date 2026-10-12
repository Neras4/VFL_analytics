import copy
import json
import pytest
from dataclasses import replace
from vfl_analytics.results import ResultStatus
from vfl_analytics.rule_data import load_rule_data,validate_data,validate_all,RuleDataError
from vfl_analytics.positions import position_modifier,style_position_category,validate_formation
from vfl_analytics.weather import weather_strength
from vfl_analytics.cohesion import cohesion_bonus
from vfl_analytics.abilities import (catalog,ability_lookup,ability_components,captain_coefficient,captain_contribution,
                                    donor_contributions,idol_attendance,commercial_ticket_price,penalty_bonus)
from vfl_analytics.rules import collision
from vfl_analytics.models import STYLE_NAMES,PositionPlan
from test_models import roster,SLOTS


@pytest.mark.synthetic
def test_data_integrity_dimensions_and_caller_mutation():
    assert validate_all()['weather_logical_cells']==58464
    data=load_rule_data('core.json'); data['cohesion']['max_matches']=1
    assert load_rule_data('core.json')['cohesion']['max_matches']==25
    broken=load_rule_data('weather.json.gz'); broken['rows']['solar']['15'].pop()
    with pytest.raises(RuleDataError): validate_data('weather.json.gz',broken)
    broken=load_rule_data('style_positions.json'); broken['style_positions']['numeric_coefficients']={}
    with pytest.raises(RuleDataError): validate_data('style_positions.json',broken)
    broken=load_rule_data('abilities.json'); broken['abilities'].pop()
    with pytest.raises(RuleDataError): validate_data('abilities.json',broken)


@pytest.mark.rule_reference
@pytest.mark.parametrize('native,slot,expected',[(('LD',),'LD',1),(('CM','CD'),'DM',1.05),
    (('CD','CM'),'DM',1.05),(('CM',),'DM',.95),(('CM','CF'),'AM',1.05),
    (('LM','LF'),'LW',1.05),(('RM','RF'),'RW',1.05),(('LD','LM'),'LB',1.05),
    (('RD','RM'),'RB',1.05),(('CD',),'SW',1),(('CF',),'ST',1),(('LD',),'FR',1),
    (('CF',),'LD',.7),(('CD',),'AM',.75),(('LF',),'DM',.65),(('GK',),'GK',1)])
def test_published_position_cells(native,slot,expected):
    result=position_modifier(native,slot)
    assert result.status==ResultStatus.EXACT and result.value==expected


@pytest.mark.synthetic
@pytest.mark.parametrize('native,slot',[(('GK',),'CM'),(('CM',),'GK')])
def test_gk_cannot_play_outfield(native,slot):
    assert position_modifier(native,slot).status==ResultStatus.NOT_APPLICABLE


@pytest.mark.synthetic
def test_special_slot_context():
    assert validate_formation(SLOTS)['unverified_tactical_slots']==['DM','AM']
    assert validate_formation(SLOTS,tactical_permissions={'DM':True,'AM':True})['unverified_tactical_slots']==[]
    with pytest.raises(ValueError): validate_formation(SLOTS,tactical_permissions={'DM':False})
    with pytest.raises(ValueError): validate_formation(('GK','SW','LD','RD','LM','CM1','CM2','RM','LF','CF','RF'))
    with pytest.raises(ValueError): validate_formation(SLOTS,base_slots=SLOTS)


@pytest.mark.rule_reference
@pytest.mark.parametrize('style,position,mode,category',[('bb','ST',None,'special_bonus'),
    ('british','LW',None,'special_bonus'),('spartak','AM',None,'special_bonus'),
    ('bb','CD','line','bonus'),('bb','CD','sweeper','neutral'),('normal','CD',None,'neutral')])
def test_qualitative_categories(style,position,mode,category):
    result=style_position_category(style,position,mode)
    assert result['category']==category
    assert result['numeric']['status']==('EXACT' if style=='normal' else 'UNKNOWN')


@pytest.mark.synthetic
def test_category_missing_defense_context_is_not_a_percentage():
    result=style_position_category('bb','CD')
    assert result['category'] is None
    assert result['categories']==['bonus','neutral']
    assert result['numeric']['value'] is None


@pytest.mark.rule_reference
@pytest.mark.parametrize('style,strength,weather,temp,expected',[
    ('spartak',15,'VERY_HOT',30,32),('bb',350,'VERY_HOT',30,141),
    ('spartak',350,'HOT',29,177),('bb',350,'HOT',29,152),
    ('brazil',100,'CLOUDY',20,99),('tiki',100,'CLOUDY',20,99),
    ('british',100,'CLOUDY',20,99),('catenaccio',100,'CLOUDY',20,99)])
def test_official_weather_cells(style,strength,weather,temp,expected):
    result=weather_strength(style,strength,weather,temp)
    assert result.status==ResultStatus.EXACT
    assert result.value==expected and result.unit=='strength_points'


@pytest.mark.synthetic
@pytest.mark.parametrize('style,strength,weather,temp',[('normal',100,'CLOUDY',20),
    ('spartak',14,'CLOUDY',20),('spartak',351,'CLOUDY',20),('spartak',100.5,'CLOUDY',20),
    ('spartak',100,'RAIN',0),('spartak',None,'CLOUDY',20),('spartak',100,'CLOUDY',21)])
def test_weather_unsupported_is_unknown(style,strength,weather,temp):
    result=weather_strength(style,strength,weather,temp)
    assert result.status==ResultStatus.UNKNOWN and result.value is None


@pytest.mark.synthetic
@pytest.mark.parametrize('style,strength,weather,temp',[('bad',100,'CLOUDY',20),
    ('bb',True,'CLOUDY',20),('bb',float('nan'),'CLOUDY',20),('bb',100,'fake',20),('bb',100,'CLOUDY',True)])
def test_weather_invalid_inputs(style,strength,weather,temp):
    with pytest.raises(ValueError): weather_strength(style,strength,weather,temp)


@pytest.mark.rule_reference
@pytest.mark.parametrize('code,style,expected',[('Ск','bb',.4),('Г','british',.4),('Пд','catenaccio',.4),
    ('Пк','spartak',.4),('Д','brazil',.4),('Км','tiki',.4),('Пк','normal',.2)])
def test_published_style_special_coefficients(code,style,expected):
    assert ability_lookup(code,4,'own_strength_style_bonus','by_level',style=style).value==expected


@pytest.mark.synthetic
@pytest.mark.parametrize('code',[x['code'] for x in catalog()])
@pytest.mark.parametrize('level',[1,2,3,4])
def test_all_21_catalogs_all_levels(code,level):
    out=ability_components(code,level,team_style='spartak',defense_formation='line',defense_type='zonal',phase='attacking',age=30)
    assert out['code']==code and out['effects']
    assert out['combined_strength']['status']=='UNKNOWN'
    assert all(x['result']['source'] for x in out['effects'])
    json.dumps(out,allow_nan=False)


@pytest.mark.rule_reference
@pytest.mark.parametrize('code,kind,param,expected',[('Р','keeper_strength','sweeper_by_level',.32),
    ('В','keeper_strength','line_by_level',.32),('От','defensive_action_strength','zone_by_level',.32),
    ('Оп','defensive_action_strength','man_by_level',.32),('У','attacking_action_strength','by_level',.2),
    ('И','team_donor_strength','by_level',.03),('Л','line_donor_strength','by_level',.12),
    ('Ат','post_match_fatigue','reduction_pp_per_90_by_level',4),
    ('См','attacking_foul_or_penalty_earning','by_level',.4),
    ('Шт','free_kick_strength','defending_by_level',.6),('Уг','corner_strength','attacking_by_level',.2),
    ('Тр','injury_incidence_multiplier','levels0to4',.2),('П','goalkeeper_penalty_save','by_level',1.5)])
def test_nonstyle_published_coefficients(code,kind,param,expected):
    assert ability_lookup(code,4,kind,param).value==expected


@pytest.mark.rule_reference
@pytest.mark.parametrize('age,level,expected',[(16,0,-.08),(16,1,.02),(30,1,.04),
    (34,1,.08),(16,2,.06),(34,2,.08),(16,3,.09),(34,4,.12)])
def test_captain_age_ka_table(age,level,expected):
    assert captain_coefficient(age,level).value==expected


@pytest.mark.synthetic
def test_captain_real_force_gate_ka_self_exclusion():
    forces={'cap':90,'other':100}
    assert captain_contribution(34,0,'cap',forces).status==ResultStatus.UNKNOWN
    assert captain_contribution(34,0,'cap',forces,strength_basis_verified=True).value==0
    assert captain_contribution(34,4,'cap',forces,strength_basis_verified=True).value==pytest.approx(10.8)
    assert captain_contribution(16,0,'cap',forces,strength_basis_verified=True).value==-8
    assert captain_contribution(34,4,'cap',forces,strength_basis_verified=True,unresolved_modifiers=True).value is None
    assert captain_contribution(34,4,'cap',{'cap':90,'other':None},strength_basis_verified=True).value is None


@pytest.mark.synthetic
def test_leader_count_and_team_donor_scopes():
    ps=roster(); a=replace(ps[1],specials=('Л4',)); b=replace(ps[2],specials=('Л1',))
    mapping={'LD':a,'CD1':ps[2],'CM':ps[7]}; forces={a.id:100,ps[2].id:90,ps[7].id:80}
    result=donor_contributions(mapping,forces,kind='Л',strength_basis_verified=True)
    assert result[a.id]['value']==12 and result[ps[2].id]['value']==12 and result[ps[7].id]['value']==0
    mapping['CD1']=b
    assert donor_contributions(mapping,forces,kind='Л',strength_basis_verified=True)[a.id]['value']==0
    mapping={'LD':replace(a,specials=('И4',)),'CM':ps[7]}
    assert donor_contributions(mapping,forces,strength_basis_verified=True)[a.id]['value']==3
    assert donor_contributions(mapping,None)[a.id]['status']=='UNKNOWN'


@pytest.mark.rule_reference
def test_cohesion_published_example():
    ids=[str(i) for i in range(11)]
    history=[{'competitive':True,'player_ids':ids},{'competitive':True,'player_ids':ids[:-1]},
             {'competitive':True,'player_ids':['other']}]
    assert cohesion_bonus(ids,history).value==.0225


@pytest.mark.synthetic
def test_cohesion_boundary_history_and_unknown():
    ids=[str(i) for i in range(11)]
    full=[{'competitive':True,'player_ids':ids}]*30
    assert cohesion_bonus(ids,full).value==.3125
    assert cohesion_bonus(ids,[]).status==ResultStatus.BOUNDED
    assert cohesion_bonus(ids,[{'competitive':True,'player_ids':None}]).status==ResultStatus.UNKNOWN
    assert cohesion_bonus(ids,[{'competitive':False}],history_complete=True).value==0
    assert cohesion_bonus(ids,[{'competitive':True,'player_ids':ids[:4]}],history_complete=True).value==0


@pytest.mark.rule_reference
def test_idol_ticket_and_moment_components_are_not_prematch_force():
    assert idol_attendance(4,'first_team').value==.2
    assert idol_attendance(4,'reserve',player_value=20,team_value=100).value==.4
    assert idol_attendance(4,'duplicate').value==0
    assert commercial_ticket_price(10).value==15
    assert penalty_bonus(100,1,4,[{'level':4,'strength':200}],strength_basis_verified=True).value==200
    assert penalty_bonus(100,4,4,[{'level':4,'strength':200}],strength_basis_verified=True).value==300
    assert penalty_bonus(100,4,4,[],taker_is_goalkeeper=True,strength_basis_verified=True).value==0
