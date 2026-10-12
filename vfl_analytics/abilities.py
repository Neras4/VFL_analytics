"""21-ability catalog and isolated coefficient lookups, not a combined force sum."""
import copy
from fractions import Fraction
from .rule_data import _data
from .models import style_id,base_position
from .validation import number,positions
from .arithmetic import validate_age
from .results import exact,unknown,CalculationResult,ResultStatus

STYLE_KEYS={'bb':'run_and_gun','british':'british','catenaccio':'catenaccio','spartak':'spartak',
            'brazil':'brazilian','tiki':'tiki_taka','normal':'normal'}


def catalog():
    return copy.deepcopy(_data('abilities.json')['abilities'])


def ability_definition(code):
    if not isinstance(code,str):
        raise ValueError('Ability code must be a string')
    entry=next((a for a in _data('abilities.json')['abilities'] if a['code']==code),None)
    if entry is None:
        raise ValueError('Unknown ability code')
    return copy.deepcopy(entry)


def ability_profile_eligible(code,native_positions):
    native=set(positions(native_positions)); allowed=ability_definition(code)['eligible_profiles']
    profile={'all':True,'outfield':'GK' not in native,'goalkeeper':native=={'GK'},
        'defender':bool(native&{'LD','CD','RD'}),'midfielder':bool(native&{'LM','CM','RM'}),
        'forward':bool(native&{'LF','CF','RF'})}
    return any(profile[x] for x in allowed)


def ability_lookup(code,level,effect_kind,parameter,*,style=None,age=None,category=None,index=None):
    """Resolve one published parameter, requiring explicit selectors for nested tables.

    A coefficient does not assert that its activation conditions hold in a match.
    Distribution/vector fields require an index/category; no implicit total.
    """
    definition=ability_definition(code)
    number(level,'ability level',minimum=1,maximum=4,integer=True)
    effect=next((e for e in definition['effects'] if e['kind']==effect_kind),None)
    if effect is None or parameter not in effect:
        raise ValueError('Unknown published effect/parameter')
    source=definition['source']+'; page64 version 14.0 (2024-06-23)'
    value=effect[parameter]
    unit='fraction'
    if parameter=='by_level_and_age':
        if age is None:
            return unknown(source=source,reason='Captain age missing')
        validate_age(age); value=value[str(int(level))][str(age)]
    elif parameter=='ages':
        if age is None:
            return unknown(source=source,reason='Age missing')
        validate_age(age)
        if str(age) not in value:
            return CalculationResult(ResultStatus.NOT_APPLICABLE,source=source,reason='No ageing-loss row for this age')
        value=value[str(age)][int(level)]
    elif 'levels0to4' in parameter or parameter=='minimum_by_level':
        value=value[int(level)]
    elif 'by_level' in parameter and parameter not in ('combined_first_team_idol_levels_to_price',):
        value=value[str(int(level))] if isinstance(value,dict) else value[int(level)-1]
    if isinstance(value,dict):
        if style is not None:
            normalized=style_id(style)
            if normalized is None:
                return unknown(source=source,reason='Team style missing')
            value=value.get(STYLE_KEYS[normalized])
        elif category is not None:
            if category not in value:
                raise ValueError('Unknown effect category')
            value=value[category]
        else:
            return unknown(source=source,reason='Explicit table selector required')
    if isinstance(value,list):
        if index is None:
            return unknown(source=source,reason='Explicit vector entry required')
        number(index,'vector index',minimum=0,maximum=len(value)-1,integer=True)
        value=value[int(index)]
    if value is None:
        return unknown(source=source,reason='Numerical coefficient not published')
    if not isinstance(value,(int,float)):
        raise ValueError('Selected parameter is descriptive, not numeric')
    if '_pp' in parameter:
        unit='percentage_points_per_90_minutes' if 'per_90' in parameter else 'percentage_points'
    if 'severity' in effect_kind:
        unit='conditional_probability'
    return exact(value,unit=unit,source=source,reason='Isolated published coefficient; activation, base and order remain separate')


def ability_components(code,level,*,team_style=None,defense_formation=None,defense_type=None,phase=None,age=None,native_positions=None):
    """Applicable primary components plus complete source catalog of every effect."""
    definition=ability_definition(code); number(level,'level',minimum=1,maximum=4,integer=True)
    source=definition['source']; results=[]
    if native_positions is not None and not ability_profile_eligible(code,native_positions):
        return {'code':code,'level':level,'effects':[],
                'result':CalculationResult(ResultStatus.NOT_APPLICABLE,source=source,reason='Native-profile restriction').to_dict()}
    if defense_formation not in (None,'line','sweeper') or defense_type not in (None,'zonal','personal') or phase not in (None,'attacking','defending'):
        raise ValueError('Unsupported tactical context')
    for effect in definition['effects']:
        kind=effect['kind']; param=None
        selectors={}
        if kind=='own_strength_style_bonus':
            if team_style is not None:
                param='by_level'; selectors['style']=team_style
        elif kind=='captain_coefficient':
            param='by_level_and_age'; selectors['age']=age
        elif kind in ('team_donor_strength','line_donor_strength','attacking_action_strength',
                      'attacking_foul_or_penalty_earning','defensive_card_probability',
                      'outfield_own_penalty_bonus','outfield_helper','goalkeeper_penalty_save'):
            param='by_level'
        elif kind=='keeper_strength' and defense_formation is not None:
            param=defense_formation+'_by_level'
        elif kind=='defensive_action_strength' and defense_type is not None:
            param={'zonal':'zone_by_level','personal':'man_by_level'}[defense_type]
        elif kind in ('free_kick_strength','corner_strength') and phase is not None:
            param=phase+'_by_level'
        elif kind=='post_match_fatigue':
            param='reduction_pp_per_90_by_level'
        elif kind=='injury_incidence_multiplier':
            param='levels0to4'
        elif kind=='ageing_strength_loss_fraction':
            param='ages'; selectors['age']=age
        result=ability_lookup(code,level,kind,param,**selectors) if param else unknown(source=source,
            reason='Context-specific/qualitative effect; choose published parameter explicitly with ability_lookup')
        if kind=='goalkeeper_penalty_taker':
            result=CalculationResult(ResultStatus.NOT_APPLICABLE,source=source,reason='Goalkeeper П grants no own shooting bonus')
        results.append({'kind':kind,'scope':effect_scope(kind),'result':result.to_dict(),'conditions':definition['activation_conditions']})
    return {'code':code,'name':definition['name_ru'],'level':level,'effects':results,
            'catalog':definition,'combined_strength':unknown(unit='strength_points',source=source,
               reason='Effects belong to distinct phases/bases; stacking/order unresolved').to_dict()}


def effect_scope(kind):
    if kind=='own_strength_style_bonus': return 'prematch_strength'
    if kind in ('keeper_strength','captain_coefficient','team_donor_strength','line_donor_strength'): return 'conditional_match_strength'
    if any(x in kind for x in ('fatigue','ageing','injury','attendance','revenue','ticket')): return 'fatigue_season_economic'
    return 'moment_specific'


def captain_coefficient(age,ka_level=0):
    validate_age(age); number(ka_level,'Ka level',minimum=0,maximum=4,integer=True)
    effect=ability_definition('Ка')['effects'][0]
    return exact(effect['by_level_and_age'][str(int(ka_level))][str(age)],source=ability_definition('Ка')['source'],
                 reason='Age/Ka table; strength-base and weak-captain gate separate')


def captain_contribution(age,ka_level,captain_id,on_pitch_strengths,*,strength_basis_verified=False,unresolved_modifiers=False):
    coeff=captain_coefficient(age,ka_level); source=coeff.source
    if not isinstance(strength_basis_verified,bool) or not isinstance(unresolved_modifiers,bool):
        raise ValueError('Verification/modifier flags must be boolean')
    if on_pitch_strengths is None or not strength_basis_verified or unresolved_modifiers:
        return unknown(unit='strength_points',source=source,reason='Verified current real positional forces required; partial/collector force is not an unconditional substitute')
    if not isinstance(on_pitch_strengths,dict) or captain_id not in on_pitch_strengths or not 2<=len(on_pitch_strengths)<=11:
        raise ValueError('Captain must be one of 2..11 on-field players')
    if any(s is None for s in on_pitch_strengths.values()):
        return unknown(unit='strength_points',source=source,reason='Missing current on-field force')
    for strength in on_pitch_strengths.values(): number(strength,'real positional strength',minimum=0)
    forces={sid:Fraction(str(value)) for sid,value in on_pitch_strengths.items()}
    captain=forces[captain_id]
    coefficient=Fraction(str(coeff.value))
    if coefficient>0 and ka_level==0 and captain<sum(forces.values())/len(forces):
        return exact(0.,unit='strength_points',source=source,reason='Positive ordinary captain suppressed below real-position mean')
    delta=coefficient*(captain*(len(forces)-1) if coefficient>=0 else sum(forces.values())-captain)
    return exact(float(delta),unit='strength_points',source=source,reason='Isolated team captain delta, self excluded, conditional on verified strength stage')


def donor_contributions(players_by_slot,on_pitch_strengths,*,kind='И',strength_basis_verified=False):
    """Individual И and exactly-one-per-line Л contributions. No unverified stacking."""
    if kind not in ('И','Л') or not isinstance(strength_basis_verified,bool):
        raise ValueError('Invalid donor context')
    definition=ability_definition(kind); effect=definition['effects'][0]
    donors=[]
    from .validation import special
    for slot,p in players_by_slot.items():
        for token in p.specials:
            code,level=special(token)
            if code==kind: donors.append((slot,p,level))
    results={}
    for slot,p in players_by_slot.items():
        relevant=donors
        if kind=='Л':
            line=next((name for name,pos in effect['line_positions'].items() if base_position(slot) in pos),None)
            relevant=[d for d in donors if base_position(d[0]) in effect['line_positions'][line]]
        if not relevant or kind=='Л' and len(relevant)!=1 or kind=='И' and p.is_league_player:
            results[p.id]=exact(0.,unit='strength_points',source=definition['source'],reason='No active donor / multiple leaders suppressed / League excluded')
        elif not strength_basis_verified or on_pitch_strengths is None or any(on_pitch_strengths.get(d[1].id) is None for d in relevant):
            results[p.id]=unknown(unit='strength_points',source=definition['source'],reason='Verified donor strength missing')
        elif kind=='И' and len(relevant)>1:
            results[p.id]=unknown(unit='strength_points',source=definition['source'],reason='Multiple donor stacking not established; inspect isolated donors separately')
        else:
            donor=relevant[0]; force=on_pitch_strengths[donor[1].id]; number(force,'donor force',minimum=0)
            results[p.id]=exact(effect['by_level'][donor[2]-1]*force,unit='strength_points',source=definition['source'],reason='Isolated published donor contribution; self included')
    return {sid:value.to_dict() for sid,value in results.items()}


def idol_attendance(level,role,*,player_value=None,team_value=None):
    number(level,'level',minimum=1,maximum=4,integer=True); effect=ability_definition('К')['effects'][0]; source=ability_definition('К')['source']
    level=int(level)
    if role is None: return unknown(source=source,reason='Roster role missing')
    if role in effect['zero_if_role']: return exact(0.,source=source)
    if role=='first_team': return exact(effect['first_team_by_level'][level-1],source=source)
    if role not in ('reserve','loan'): raise ValueError('Unsupported idol role')
    if player_value is None or team_value is None: return unknown(source=source,reason='Reserve/loan value share missing')
    number(player_value,'player_value',minimum=0); number(team_value,'team_value',positive=True)
    if player_value>team_value: raise ValueError('Player value exceeds team total')
    return exact(effect['reserve_or_loan_multiplier_by_level'][level-1]*100*player_value/team_value,source=source,
                 reason='Isolated published attendance fraction; forecast spectator cap applied separately')


def commercial_ticket_price(total_idol_levels):
    number(total_idol_levels,'idol levels',minimum=0,integer=True)
    effect=next(e for e in ability_definition('К')['effects'] if e['kind']=='commercial_tournament_ticket')
    table=effect['combined_first_team_idol_levels_to_price']
    return exact(table[str(int(total_idol_levels)) if total_idol_levels<10 else '10+'],unit='currency',source=ability_definition('К')['source'])


def penalty_bonus(taker_strength,taker_level,goalkeeper_level,helpers=(),*,taker_is_goalkeeper=False,strength_basis_verified=False):
    """Max of own penalty bonus and eligible helper aid, never their sum."""
    number(taker_level,'taker level',minimum=0,maximum=4,integer=True)
    number(goalkeeper_level,'goalkeeper level',minimum=0,maximum=4,integer=True)
    if not isinstance(taker_is_goalkeeper,bool) or not isinstance(strength_basis_verified,bool):
        raise ValueError('Penalty flags must be boolean')
    source=ability_definition('П')['source']
    if not strength_basis_verified or taker_strength is None:
        return unknown(unit='strength_points',source=source,reason='Verified moment-specific strengths missing')
    number(taker_strength,'taker force',minimum=0)
    effects={e['kind']:e for e in ability_definition('П')['effects']}
    own=0. if taker_is_goalkeeper or taker_level==0 else effects['outfield_own_penalty_bonus']['by_level'][int(taker_level)-1]*taker_strength
    aid=[]
    for helper in helpers:
        number(helper['level'],'helper level',minimum=1,maximum=4,integer=True)
        number(helper['strength'],'helper force',minimum=0)
        if helper['level']>=goalkeeper_level:
            aid.append(effects['outfield_helper']['by_level'][int(helper['level'])-1]*helper['strength'])
    return exact(max([own,*aid]),unit='strength_points',source=source,reason='Own bonus or strongest eligible aid; GK own shooting bonus excluded')
