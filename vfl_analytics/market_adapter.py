"""Transfer contracts only: no roster conversion, valuation or game actions."""
from copy import deepcopy
from .adapters import _id, _optional_num, _positions
from .validation import number, positions, special_list
from .arithmetic import validate_age
from .snapshots import collection_time


def _market_row(row, bids=False):
    if not isinstance(row, dict):
        raise ValueError('Market row must be object')
    sid = _id(row)
    validate_age(row.get('age'))
    positions(_positions(row))
    number(row.get('strength'), 'strength', positive=True)
    numeric = {}
    for key in ('fatigue','form','value','bidsCount','askingPercent','askingPrice','bidPrice','bidPercent',
                'preliminaryBidPrice','currentBidPrice','currentBidPercent'):
        value = _optional_num(row.get(key))
        if value is not None:
            number(value, key, minimum=75 if key=='form' else 0,
                   maximum=125 if key=='form' else (100 if key=='fatigue' else None),
                   integer=key in ('bidsCount','value','askingPrice','bidPrice','preliminaryBidPrice','currentBidPrice'))
        numeric[key] = value
    raw = row.get('specials')
    if raw is not None and not isinstance(raw, str):
        raise ValueError('Market specials must be string or null')
    from .validation import ABILITY_CODES
    tokens = [] if raw is None else raw.split()
    tokens = [s+'1' if s in ABILITY_CODES else s for s in tokens]
    special_list(tokens)
    style = row.get('style')
    possible = None
    if style is not None:
        if not isinstance(style, dict) or not isinstance(style.get('possibleStyles'), list):
            raise ValueError('Market style requires possibleStyles list')
        from .models import style_id
        possible = [style_id(x.get('label')) for x in style['possibleStyles'] if isinstance(x,dict)]
        if len(possible)!=len(style['possibleStyles']) or any(s in (None,'normal') for s in possible):
            raise ValueError('Invalid possible player styles')
        if len(set(possible))!=len(possible):
            raise ValueError('Duplicate possible styles')
    for key in ('growth','decline'):
        interval=row.get(key)
        if interval is None: continue
        if not isinstance(interval,dict): raise ValueError('Study range must be object')
        for name in ('percent','min','max'):
            value=interval.get(name)
            if value is not None: number(value,key+'.'+name,minimum=0,maximum=100)
        if interval.get('min') is not None and interval.get('max') is not None and interval['min']>interval['max']:
            raise ValueError('Reversed study range')
    if bids and not isinstance(row.get('bidType'), str):
        raise ValueError('Bid status required')
    return {'player_id':sid, 'positions':list(_positions(row)), 'age':row['age'], 'strength':row['strength'],
            **numeric, 'specials':list(special_list(tokens)), 'specials_known':raw is not None,
            'possible_styles':possible, 'favorite_style_verified':False,
            'observation':deepcopy(row)}


def adapt_market_snapshot(snapshot):
    if not isinstance(snapshot,dict): raise ValueError('Snapshot must be object')
    kind=snapshot.get('kind')
    if kind not in ('vfl-transfer-market','vfl-transfer-bids'):
        raise ValueError('Expected market or bids snapshot')
    collection_time(snapshot.get('generatedAt'))
    management=snapshot.get('management')
    if not isinstance(management,dict) or not isinstance(management.get('transferMarket'),dict):
        raise ValueError('management.transferMarket must be object')
    market=management['transferMarket']; bids=kind=='vfl-transfer-bids'
    section=market.get('myBids' if bids else 'search')
    if not isinstance(section,dict): raise ValueError('Missing market observation section')
    collected=section.get('collectedAt') if bids else market.get('collectedAt')
    collection_time(collected)
    rows=section.get('bids' if bids else 'players')
    if not isinstance(rows,list): raise ValueError('Market rows must be list')
    issues=[]; accepted=[]; seen=set()
    for index,row in enumerate(rows):
        try:
            item=_market_row(row,bids)
            if item['player_id'] in seen: raise ValueError('Duplicate market player')
            seen.add(item['player_id']); accepted.append(item)
        except (ValueError,TypeError,AttributeError) as exc:
            issues.append(f'row[{index}]:invalid:{exc}')
    result={'kind':kind,'generatedAt':snapshot['generatedAt'],'collectedAt':collected,
            'total_rows':len(rows),'accepted':len(accepted),'rejected':len(rows)-len(accepted),
            'rows':accepted,'issues':issues,'roster_players':[],
            'utility_model':None,'observation':deepcopy(section)}
    if bids:
        limits=section.get('purchaseLimits')
        if not isinstance(limits,dict): raise ValueError('purchaseLimits must be object')
        for key,value in limits.items(): number(value,'purchaseLimits.'+key,minimum=0,integer=True)
        result['purchase_limits']=deepcopy(limits)
        result['state_semantics']='Independent observation; never union successive bid states'
    else:
        pagination=section.get('pagination'); sort=section.get('sort'); filters=section.get('filters')
        if not all(isinstance(x,dict) for x in (pagination,sort,filters)):
            raise ValueError('pagination, sort and filters must be objects')
        for key in ('totalResults','totalPages','page','pageSize','shownFrom','shownTo'):
            number(pagination.get(key),'pagination.'+key,minimum=1 if key in ('page','pageSize') else 0,integer=True)
        total=pagination['totalResults']; start=pagination['shownFrom']; end=pagination['shownTo']
        if end>total or end<start or (end-start+1 if total else 0)!=len(rows) or len(rows)>pagination['pageSize']:
            issues.append('pagination:inconsistent_range_or_count')
        expected_pages=(total+pagination['pageSize']-1)//pagination['pageSize']
        if pagination['totalPages']!=expected_pages or pagination['page']>max(1,expected_pages):
            issues.append('pagination:inconsistent_pages')
        if not isinstance(sort.get('applied'),bool) or not isinstance(sort.get('requested'),str):
            raise ValueError('sort.requested string and sort.applied boolean required')
        for key,value in filters.items():
            if isinstance(value,dict) and ('min' in value or 'max' in value):
                for bound in ('min','max'):
                    if value.get(bound) is not None: number(value[bound],'filters.'+key,minimum=0)
                if value.get('min') is not None and value.get('max') is not None and value['min']>value['max']:
                    raise ValueError('Reversed filter range')
        result.update(pagination=deepcopy(pagination),filters=deepcopy(filters),sort=deepcopy(sort),
                      complete=len(rows)==total and len(accepted)==total and not issues)
        if len(rows)<total: issues.append('incomplete_search_snapshot')
        if not sort['applied']: issues.append('requested_sort_not_applied')
    return result
