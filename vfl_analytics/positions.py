"""Position suitability is numerical; team-style colors are a separate component."""
from .models import base_position,style_id
from .validation import positions, NATIVE_POSITIONS,SPECIAL_POSITIONS
from .rule_data import _data
from .results import exact,unknown,CalculationResult,ResultStatus

SOURCE='https://vfliga.com/rules.php?page=159 §1–3, version 2.1 (2024-10-10)'


def position_modifier(native_positions,slot):
    native=positions(native_positions); target=base_position(slot)
    if target not in NATIVE_POSITIONS | SPECIAL_POSITIONS:
        raise ValueError('Unknown tactical position')
    if ('GK' in native)!=(target=='GK'):
        return CalculationResult(ResultStatus.NOT_APPLICABLE,source=SOURCE,reason='GK/outfield assignment prohibited')
    data=_data('core.json')
    table=data['position_profile_pct'].get(target,data['position_special_pct'].get(target))
    if target=='GK' or target=='FR':
        return exact(1.,source=SOURCE,reason='GK native / FR any outfield')
    matches=[]
    for percent,profiles in table.items():
        if percent=='illegal':
            continue
        for profile in profiles:
            if profile=='other' or ('/' in profile and set(profile.split('/'))<=set(native)) or profile in native:
                matches.append(int(percent))
    return exact(max(matches)/100,source=SOURCE,reason='Best applicable native or dual-position cell; not team-style bonus')


def position_eligibility(native_positions,slot):
    return position_modifier(native_positions,slot).status!=ResultStatus.NOT_APPLICABLE


def validate_formation(slots,defense_formation=None,base_slots=None,tactical_permissions=None):
    """Published page40 §5.1 transformations; missing CM tactical context stays unknown."""
    pos=[base_position(s) for s in slots]
    roots={'SW':'CD','LB':'LD','RB':'RD','DM':'CM','AM':'CM','FR':'CM','LW':'LM','RW':'RM','ST':'CF'}
    inferred=[roots.get(p,p) for p in pos]
    if base_slots is not None:
        if len(base_slots)!=len(slots) or any(base_position(s) not in NATIVE_POSITIONS for s in base_slots):
            raise ValueError('Formation base must contain matching native slots')
        if [base_position(s) for s in base_slots]!=inferred:
            raise ValueError('Special-slot transformation differs from native formation')
    if 'SW' in pos and inferred.count('CD')<2:
        raise ValueError('SW requires at least two original central defenders (page40 §5.1)')
    if defense_formation=='line' and 'SW' in pos:
        raise ValueError('SW is incompatible with line defence')
    permissions=tactical_permissions or {}
    if not isinstance(permissions,dict) or any(k not in slots or v is not None and not isinstance(v,bool) for k,v in permissions.items()):
        raise ValueError('Tactical permissions must be slot -> boolean/null')
    unknown_slots=[]
    for slot,p in zip(slots,pos):
        if p in ('DM','AM','FR'):
            if permissions.get(slot) is False:
                raise ValueError('Special position explicitly forbidden by tactical context')
            if permissions.get(slot) is not True:
                unknown_slots.append(slot)
    return {'status':'UNKNOWN' if unknown_slots else 'partial_validation',
            'unverified_tactical_slots':unknown_slots,
            'warning':'CM transformations depend on caller-verified tactics; full formation catalog not asserted'}


def style_position_category(style,slot,defense_formation=None):
    style=style_id(style); position=base_position(slot)
    if position not in NATIVE_POSITIONS | SPECIAL_POSITIONS:
        raise ValueError('Unknown tactical position')
    if defense_formation not in (None,'line','sweeper'):
        raise ValueError('Unknown defence mode')
    source='https://vfliga.com/rules.php?page=40 §2.10; https://vfliga.com/pics/styles.png'
    if style=='normal':
        return {'category':'neutral','categories':['neutral'],'numeric':exact(1.,source=source,reason='Normal style explicitly has no positional style effect').to_dict()}
    from .models import style_id as normalize
    matrix=_data('style_positions.json')['style_positions']['matrix']
    entries=next(entries for name,entries in matrix.items() if normalize(name)==style)
    mode={'sweeper':'with_SW','line':'line',None:None}[defense_formation]
    categories=sorted({e['category'] for e in entries if e['position']==position and
                       (e['central_defense_mode'] is None or mode is None or e['central_defense_mode']==mode)})
    return {'category':categories[0] if len(categories)==1 else None,'categories':categories,
            'numeric':unknown(source=source,reason='Qualitative color only; numerical multiplier not published'+
                       ('; CD defence context missing' if position=='CD' and mode is None else '')).to_dict()}
