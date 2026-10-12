"""Static Assistant boundary. Synthetic fixtures are not observed-export acceptance."""
import math
import re
from .models import Player, STYLE_ALIASES
from .validation import identity


def _optional_num(value):
    if isinstance(value,dict):
        value=value.get('value',value.get('number'))
    if value is None or isinstance(value,str) and value.strip() in ('','?','—','-'):
        return None
    if isinstance(value,bool):
        raise ValueError('Boolean is not a number')
    if isinstance(value,str):
        raw=re.sub(r'[\s\u00a0%]','',value).replace(',','.')
        try:
            value=float(raw)
        except ValueError:
            raise ValueError('Malformed numeric field') from None
    if not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError('Numeric field must be finite')
    return value


def _positions(row):
    raw=row.get('positions',row.get('position'))
    if isinstance(raw,str):
        return tuple(x for x in re.split(r'[/, ]+',raw) if x)
    return raw


def _id(row):
    result=identity(row.get('playerId',row.get('id')),collector=True)
    if 'playerId' in row and 'id' in row and identity(row['id'],collector=True)!=result:
        raise ValueError('Conflicting playerId/id')
    return result


def adapt_roster(snapshot):
    if not isinstance(snapshot,dict):
        raise ValueError('Snapshot must be an object')
    roster=snapshot.get('roster',snapshot.get('team',{}).get('roster',{}))
    if isinstance(roster,dict):
        rows=roster.get('players',snapshot.get('players',[]))
    else:
        rows=roster
    if not isinstance(rows,list):
        raise ValueError('roster.players must be a list')
    details=snapshot.get('playerDetails',[])
    if not isinstance(details,list):
        raise ValueError('playerDetails must be a list')
    issues=[]; by_id={}; ambiguous=set()
    for index,detail in enumerate(details):
        try:
            if not isinstance(detail,dict):
                raise ValueError('Detail must be an object')
            sid=_id(detail)
            for key in ('info','stats','contract'):
                child=detail.get(key)
                if child is not None and not isinstance(child,dict):
                    raise ValueError(f'{key} must be object or null')
                if child and child.get('playerId') is not None and identity(child['playerId'],collector=True)!=sid:
                    raise ValueError('Nested detail playerId mismatch')
            if sid in by_id or sid in ambiguous:
                ambiguous.add(sid); by_id.pop(sid,None)
                issues.append(f'detail[{index}]:duplicate_player_details:{sid}')
            else:
                by_id[sid]=detail
        except ValueError as exc:
            issues.append(f'detail[{index}]:invalid:{exc}')
    season=snapshot.get('rosterSeasonStats')
    season_by_id={}
    if season is not None:
        if not isinstance(season,dict) or not isinstance(season.get('players'),list):
            raise ValueError('rosterSeasonStats must contain players list')
        scope=season.get('scope') or {}
        if scope.get('sort')!=300 or scope.get('label')!='по всем турнирам':
            issues.append('rosterSeasonStats:unverified_all_tournament_scope')
        for record in season['players']:
            try:
                sid=_id(record)
                if sid in season_by_id:
                    raise ValueError('Duplicate season-stat player ID')
                season_by_id[sid]=record
            except (ValueError,TypeError,AttributeError) as exc:
                issues.append(f'rosterSeasonStats:invalid:{exc}')
    players=[]; evidence={}; seen=set()
    for index,row in enumerate(rows):
        prefix=f'row[{index}]'
        try:
            if not isinstance(row,dict):
                raise ValueError('Roster row must be an object')
            sid=_id(row)
            if sid in seen:
                raise ValueError('Duplicate roster player ID')
            seen.add(sid)
            detail=by_id.get(sid,{})
            if not detail:
                issues.append(f'{prefix}:missing_or_ambiguous_player_details')
            info=detail.get('info') or {}
            contract=detail.get('contract') or {}
            current_contract=contract.get('current') or {}
            # A present roster key, including null, always wins over profile copies.
            def field(key, alternate=None):
                if key in row:
                    return row[key]
                if key in detail:
                    return detail[key]
                return info.get(key) if alternate is None else alternate
            age=_optional_num(field('age')); strength=_optional_num(field('strength'))
            if age is None or strength is None or not row.get('name') or not _positions(row):
                issues.append(f'{prefix}:missing_id_name_age_strength_or_position')
                continue
            if age!=int(age):
                raise ValueError('Fractional age')
            favorite=row.get('favoriteStyle',row.get('favorite_style',info.get('style')))
            if isinstance(favorite,dict):
                favorite=favorite.get('label',favorite.get('name'))
            if favorite is not None and (not isinstance(favorite,str) or favorite.strip().casefold() not in STYLE_ALIASES):
                issues.append(f'{prefix}:unverified_favorite_style')
                favorite=None
            known=_optional_num(row.get('styleKnownPercent',row.get('style_known_percent')))
            if known is not None and known!=int(known):
                raise ValueError('Fractional style study percentage')
            fatigue=_optional_num(field('fatigue')); form=_optional_num(field('form'))
            minutes=info.get('seasonMinutes')
            if minutes is None and isinstance(info.get('usefulness'),dict):
                minutes=info['usefulness'].get('minutes')
            p=Player(id=sid,name=row['name'],positions=_positions(row),age=int(age),strength=strength,
                     fatigue=fatigue,form=form,real_strength=_optional_num(field('realStrength')),
                     favorite_style=favorite,style_known_percent=None if known is None else int(known),
                     nationality=row.get('country',row.get('nationality')),
                     specials=row.get('specials',detail.get('specials',[])),available=row.get('available'),
                     value=_optional_num(field('value')),
                     salary_per_tour=_optional_num(field('salaryPerTour',current_contract.get('salaryPerTour'))),
                     played_minutes=_optional_num(minutes),is_league_player=row.get('isLeaguePlayer',False))
            players.append(p)
            if fatigue is None or form is None:
                issues.append(f'{prefix}:unknown_form_or_fatigue')
            for label,value in [('favorite_style',favorite),('style_study',known),('contract',contract or None)]:
                if value is None:
                    issues.append(f'{prefix}:missing_{label}')
            evidence[sid]={'selectedStats':row.get('selectedStats'),
                          'rosterSeasonStats':season_by_id.get(sid),
                          'rosterSeasonStatsScope':None if season is None else season.get('scope'),
                          'contract':contract or None,'formTrend':row.get('formTrend'),
                          'recentMatches':info.get('recentMatches'),
                          'style_label_is_not_verification':True}
        except (ValueError,TypeError) as exc:
            issues.append(f'{prefix}:invalid:{exc}')
    for sid in sorted(set(by_id)-seen):
        issues.append(f'orphan_player_details:{sid}')
    return {'players':players,'issues':issues,'accepted':len(players),'total':len(rows),
            'evidence_by_id':evidence,
            'note':'Static Assistant source contract + SYNTHETIC fixtures; real Normal/Deep acceptance deferred to v0.2.3'}
