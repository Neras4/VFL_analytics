"""Versioned, checksum-verified offline rule data packaged with the engine."""
import copy
import gzip
import hashlib
import json
import math
from functools import lru_cache
from importlib.resources import files
from .validation import ABILITY_CODES


class RuleDataError(ValueError):
    pass


def validate_data(name,data):
    if not isinstance(data,dict) or not isinstance(data.get('schema_version'),str) or not isinstance(data.get('provenance'),dict):
        raise RuleDataError('Missing schema/provenance: '+name)
    def finite(value):
        if isinstance(value,float) and not math.isfinite(value):
            raise RuleDataError('Nonfinite rule coefficient')
        if isinstance(value,dict):
            for child in value.values(): finite(child)
        elif isinstance(value,list):
            for child in value: finite(child)
    finite(data)
    if name=='core.json':
        if len(data.get('position_profile_pct',{}))!=10 or len(data.get('position_special_pct',{}))!=9:
            raise RuleDataError('Incomplete position matrices')
        if set(data.get('captain_age_pct',{}))!={str(x) for x in range(16,35)}:
            raise RuleDataError('Captain age domain incomplete')
        if len(data.get('collision_outcomes',{}).get('cells',[]))!=7 or any(len(row)!=7 for row in data['collision_outcomes']['cells']):
            raise RuleDataError('Collision matrix dimensions')
    elif name=='abilities.json':
        abilities=data.get('abilities',[])
        if len(abilities)!=21 or {a.get('code') for a in abilities}!=set(ABILITY_CODES):
            raise RuleDataError('Ability catalog must contain 21 distinct codes')
        if any(a.get('levels')!=[1,2,3,4] or not a.get('source') or not a.get('effects') for a in abilities):
            raise RuleDataError('Invalid ability metadata')
    elif name=='style_positions.json':
        table=data['style_positions']
        if table.get('numeric_coefficients') is not None:
            raise RuleDataError('Qualitative colors cannot encode coefficients')
        if len(table['matrix'])!=6:
            raise RuleDataError('Style category matrix incomplete')
        for entries in table['matrix'].values():
            if any(e['category'] not in table['legend'] or e.get('numeric_percent') is not None for e in entries):
                raise RuleDataError('Invalid qualitative category')
    elif name=='weather.json.gz':
        if len(data.get('temperatures',[]))!=29 or len(data.get('style_groups',{}))!=6:
            raise RuleDataError('Invalid weather column/style dimensions')
        count=0
        for rows in data['rows'].values():
            if set(rows)!={str(x) for x in range(15,351)}:
                raise RuleDataError('Invalid weather strength rows')
            for row in rows.values():
                if len(row)!=29 or any(type(x)!=int or x<0 for x in row):
                    raise RuleDataError('Invalid weather cells')
                count+=len(row)
        if count!=19488 or data.get('logical_cell_count')!=58464:
            raise RuleDataError('Weather cell count mismatch')
    else:
        raise RuleDataError('Unsupported data file: '+name)
    return data


@lru_cache(maxsize=1)
def _manifest():
    return json.loads(files('vfl_analytics').joinpath('data/manifest.json').read_text(encoding='utf8'))['files']


@lru_cache(maxsize=4)
def _data(name):
    if name not in _manifest():
        raise RuleDataError('Unknown dataset')
    raw=files('vfl_analytics').joinpath('data/'+name).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=_manifest()[name]:
        raise RuleDataError('Rule data checksum mismatch: '+name)
    if name.endswith('.gz'):
        raw=gzip.decompress(raw)
    return validate_data(name,json.loads(raw))


def load_rule_data(name):
    """Caller-owned copy; lookups use private cached data without repeated copies."""
    return copy.deepcopy(_data(name))


def validate_all():
    for name in _manifest():
        _data(name)
    return {'status':'valid','datasets':len(_manifest()),'abilities':21,'weather_logical_cells':58464}


if __name__=='__main__':
    print(json.dumps(validate_all()))
