"""Strict JSON boundary validation; absence is handled by callers."""
import math
import re
from numbers import Real

NATIVE_POSITIONS = frozenset(('GK','LD','CD','RD','LM','CM','RM','LF','CF','RF'))
SPECIAL_POSITIONS = frozenset(('SW','LB','RB','DM','AM','LW','RW','ST','FR'))
ABILITY_CODES = ('Ск','Г','Пд','Пк','Д','Км','От','Оп','У','В','Р','Л','Ат','К','Шт','Уг','П','См','Тр','Ка','И')


def number(value, name, *, minimum=None, maximum=None, positive=False, integer=False):
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value):
        raise ValueError(f'{name}: finite number required')
    if integer and int(value) != value:
        raise ValueError(f'{name}: integer required')
    if (positive and value <= 0) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError(f'{name}: outside supported range')
    return value


def identity(value, *, collector=False):
    if collector:
        if isinstance(value,int) and not isinstance(value,bool) and value > 0:
            return str(value)
        if isinstance(value,str) and re.fullmatch(r'[0-9]+',value) and int(value)>0:
            return str(int(value))
    elif isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_:-]+',value):
        return value
    raise ValueError('Invalid player ID')


def positions(value):
    if not isinstance(value,(tuple,list)) or not 1 <= len(value) <= 2 or any(not isinstance(p,str) for p in value):
        raise ValueError('One or two native positions required')
    pos=tuple(p.strip().upper() for p in value)
    if len(set(pos)) != len(pos) or not set(pos) <= NATIVE_POSITIONS:
        raise ValueError('Unknown, duplicate or non-native player positions')
    if 'GK' in pos and len(pos)!=1:
        raise ValueError('GK cannot have a second position')
    if len(pos)==2:
        a,b=pos
        same_line = any({a,b} <= set(line) for line in [('LD','CD','RD'),('LM','CM','RM'),('LF','CF','RF')])
        adjacent_axis = frozenset(pos) in {frozenset(pair) for pair in [('LD','LM'),('LM','LF'),('CD','CM'),('CM','CF'),('RD','RM'),('RM','RF')]}
        if not same_line and not adjacent_axis:
            raise ValueError('Unsupported native position combination (page159 §1.2)')
    return pos


def special(value):
    if not isinstance(value,str):
        raise ValueError('Special ability must be code plus level 1..4')
    match=re.fullmatch(r'('+ '|'.join(ABILITY_CODES) +r')([1-4])',value)
    if not match:
        raise ValueError(f'Invalid special ability: {value!r}')
    return match[1],int(match[2])


def special_list(values):
    if not isinstance(values,(tuple,list)) or len(values)>4:
        raise ValueError('Specials must be a list of at most four abilities')
    parsed=[special(v) for v in values]
    if len({code for code,_ in parsed}) != len(parsed):
        raise ValueError('Duplicate special ability')
    return tuple(values)
