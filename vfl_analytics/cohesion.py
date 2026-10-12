"""History-based team cohesion, distinct from interpersonal chemistry."""
from fractions import Fraction
from .rule_data import _data
from .validation import identity
from .results import exact,unknown,bounded

SOURCE='https://vfliga.com/rules.php?page=167, version 2.0 (2020-03-30)'


def cohesion_bonus(current_player_ids,history,*,history_complete=False):
    if current_player_ids is None or history is None:
        return unknown(source=SOURCE,reason='Current lineup or chronological same-season competitive history missing')
    if not isinstance(history_complete,bool):
        raise ValueError('history_complete must be boolean')
    ids=[identity(x) for x in current_player_ids]
    if len(ids)!=len(set(ids)) or not 1<=len(ids)<=11:
        raise ValueError('Current on-field IDs must be unique, at most 11')
    table=_data('core.json')['cohesion']
    total=Fraction(0); inspected=0; stopped=False
    for record in history:
        if not isinstance(record,dict) or not isinstance(record.get('competitive'),bool):
            raise ValueError('Each history record requires explicit competitive status')
        if not record['competitive']:
            continue
        if inspected>=table['max_matches']:
            break
        participants=record.get('player_ids')
        if participants is None:
            return unknown(source=SOURCE,reason='Missing participants interrupts reliable history evaluation')
        past=[identity(x) for x in participants]
        if len(set(past))!=len(past):
            raise ValueError('Duplicate historical participant')
        overlap=len(set(ids)&set(past)); inspected+=1
        if overlap<table['stop_overlap_less_than']:
            stopped=True; break
        total+=Fraction(str(table['overlap_bonus_pct'][str(overlap)]))/100
    if stopped or inspected>=25 or history_complete:
        return exact(float(total),source=SOURCE,reason='Latest-first, same-season history; all participants who played at least one minute')
    remaining=table['max_matches']-inspected
    # Only current-player overlap is possible; fewer than six players add zero.
    maximum=Fraction(str(table['overlap_bonus_pct'].get(str(len(ids)),0)))/100
    return bounded(float(total),float(total+remaining*maximum),source=SOURCE,
                   reason='Incomplete trailing history; conservative remaining-match bound')
