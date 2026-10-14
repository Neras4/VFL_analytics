"""Bounded same-geometry counterfactuals; deltas concern the explicit proxy only."""
from .models import base_position
from .lineup import _eligible, _position_factor, _heuristic
from .rules import partial_strength_range
from .validation import special
from .abilities import ability_components


OMITTED=['Goalkeeper В/Р and other special effects not stacked into proxy',
         'Captain/Ка/И/Л absolute force bases and stacking order',
         'Chemistry geometry and cohesion participant history','Full generator/availability/tactics/weather']


def explain_lineup(players,plan,candidate):
    by_id={p.id:p for p in players};style=candidate['style']
    mapping={row['slot']:by_id[row['player_id']] for row in candidate['lineup']}
    selected={p.id for p in mapping.values()};comparisons=[]
    def inputs(p,slot):
        factor=_position_factor(p,plan,style,slot)
        return {'player_id':p.id,'name':p.name,'nominal_strength':p.strength,'form':p.form,'fatigue':p.fatigue,
            'native_positions':list(p.positions),'assigned_slot':slot,'off_primary_position':base_position(slot)!=p.positions[0],
            'specials':list(p.specials),'favorite_style':p.favorite_style,'style_known_percent':p.style_known_percent,
            'position_factor':factor,'proxy':_heuristic(p,style,factor),
            'conditional_partial':partial_strength_range(p,style,factor).to_dict()}
    def add(kind,changes):
        before=[inputs(mapping[slot],slot) for slot in changes]
        after=[inputs(p,slot) for slot,p in changes.items()]
        delta=sum(x['proxy'] for x in after)-sum(x['proxy'] for x in before)
        intervals=[x['conditional_partial'] for x in before+after]
        def bounds(r):
            if r['value'] is not None:return r['value'],r['value']
            if r['lower'] is not None:return r['lower'],r['upper']
            return None
        bs=[bounds(r) for r in intervals];n=len(before)
        low=high=None
        if all(b is not None for b in bs):
            low=sum(b[0] for b in bs[n:])-sum(b[1] for b in bs[:n])
            high=sum(b[1] for b in bs[n:])-sum(b[0] for b in bs[:n])
        changed={**mapping,**changes}
        comparisons.append({'kind':kind,'before':before,'after':after,'proxy_delta_alternative_minus_selected':delta,
            'conditional_delta_interval':{'lower':low,'upper':high,'unit':'partial_strength_units'},
            'alternative_lineup':[{'slot':s,'player_id':p.id} for s,p in changed.items()],
            'reason':'Selected assignment has larger known proxy' if delta<0 else ('Proxy tie; omitted effects may decide' if delta==0 else 'Alternative has larger proxy under this restricted comparison'),
            'status':'ESTIMATED','full_preference_status':'UNKNOWN','omitted_effects':OMITTED,
            'sensitivity':{'full_model':'UNKNOWN','reason':'Omitted effects have no justified common numerical bound',
                'conditional_order_robust':low is not None and (low>0 or high<0)}})
    bench=[p for p in players if p.id not in selected]
    for slot,p in mapping.items():
        eligible=[b for b in bench if _eligible(b,slot)]
        eligible.sort(key=lambda b:(-_heuristic(b,style,_position_factor(b,plan,style,slot)),b.id))
        chosen=eligible[:2]
        captain=next((b for b in eligible if any(code=='Ка' for code,_ in map(special,b.specials))),None)
        if captain and captain not in chosen:chosen.append(captain)
        for b in chosen:add('same_slot_replacement',{slot:b})
    # All feasible pair swaps: at most 55; preserve every other player and slot.
    slots=list(mapping)
    for i,u in enumerate(slots):
        for v in slots[i+1:]:
            if _eligible(mapping[u],v) and _eligible(mapping[v],u):add('position_swap',{u:mapping[v],v:mapping[u]})
    return {'status':'DIAGNOSTIC','selected_proxy':candidate['ranking_score'],
        'selected_inputs':[inputs(p,s) for s,p in mapping.items()],
        'special_ability_components':{p.id:[ability_components(code,level,team_style=style,native_positions=p.positions,
            defense_formation=plan.defense_formation,age=p.age) for code,level in map(special,p.specials)] for p in players},
        'comparisons':comparisons,'omitted_effects':OMITTED,
        'scope':'Bounded replacements and pair swaps, no proof of nonlinear optimum; no fabricated specialty totals'}
