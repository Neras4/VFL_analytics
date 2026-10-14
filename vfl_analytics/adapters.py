"""Assistant boundary with local row errors and explicit source evidence."""
import math
import re
from .models import Player, STYLE_ALIASES
from .validation import identity,ABILITY_CODES
from .source_evidence import fatigue_observation, scouting_style


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
    team=snapshot.get('team')
    roster=snapshot.get('roster',(team.get('roster',{}) if isinstance(team,dict) else {}))
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
            issues.append('rosterSeasonStats:invalid:expected object with players list')
            season=None
    if season is not None:
        scope=season.get('scope') or {}
        if not isinstance(scope,dict) or scope.get('sort')!=300 or scope.get('label')!='по всем турнирам':
            issues.append('rosterSeasonStats:unverified_all_tournament_scope')
        ambiguous_season=set()
        for record in season['players']:
            try:
                sid=_id(record)
                if sid in season_by_id or sid in ambiguous_season:
                    ambiguous_season.add(sid);season_by_id.pop(sid,None)
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
            if not isinstance(current_contract,dict):
                raise ValueError('contract.current must be object or null')
            provenance={}; conflicts=[]
            # A present roster key, including null, always wins over profile copies.
            def field(key, alternate=None, alternate_source=None):
                candidates=[(label,source[key]) for label,source in
                            [('roster',row),('playerDetails',detail),('playerDetails.info',info)] if key in source]
                if alternate_source is not None:
                    candidates.append((alternate_source,alternate))
                if not candidates:
                    return alternate
                provenance[key]={'source':candidates[0][0],'value':candidates[0][1]}
                if any(value!=candidates[0][1] for _,value in candidates[1:]):
                    conflicts.append({'field':key,'selected_source':candidates[0][0],
                                      'observations':[{'source':label,'value':value} for label,value in candidates]})
                return candidates[0][1]
            age=_optional_num(field('age')); strength=_optional_num(field('strength'))
            if age is None or strength is None or not row.get('name') or not _positions(row):
                issues.append(f'{prefix}:missing_id_name_age_strength_or_position')
                continue
            if age!=int(age):
                raise ValueError('Fractional age')
            favorite=row.get('favoriteStyle',row.get('favorite_style',info.get('style')))
            if isinstance(favorite,dict):
                favorite=favorite.get('label',favorite.get('name'))
            if isinstance(favorite,str) and favorite.strip().casefold() in ('неизвестно','unknown','?','—',''):
                favorite=None
            if favorite is not None and (not isinstance(favorite,str) or favorite.strip().casefold() not in STYLE_ALIASES):
                issues.append(f'{prefix}:unverified_favorite_style')
                favorite=None
            known=_optional_num(row.get('styleKnownPercent',row.get('style_known_percent')))
            if known is not None and known!=int(known):
                raise ValueError('Fractional style study percentage')
            field('fatigue')  # Retain raw disagreement evidence independently of selection.
            fatigue_evidence=fatigue_observation(snapshot,row,detail,info,sid)
            fatigue=_optional_num(fatigue_evidence['value']); form=_optional_num(field('form'))
            provenance['fatigue']=fatigue_evidence
            study=scouting_style(snapshot,sid,favorite,known)
            known=study['percent']
            issues.extend(f'{prefix}:{issue}' for issue in study['issues'])
            specials=row.get('specials',detail.get('specials',[]))
            specials_known=specials is not None and ('specials' in row or 'specials' in detail)
            if specials is None:
                specials=[]
            if isinstance(specials,list):
                specials=[s+'1' if s in ABILITY_CODES else s for s in specials]
            minutes=info.get('seasonMinutes')
            if minutes is None and isinstance(info.get('usefulness'),dict):
                minutes=info['usefulness'].get('minutes')
            p=Player(id=sid,name=row['name'],positions=_positions(row),age=int(age),strength=strength,
                     fatigue=fatigue,form=form,real_strength=_optional_num(field('realStrength')),
                     favorite_style=favorite,style_known_percent=None if known is None else int(known),
                     favorite_style_verified=study['verified'],
                     nationality=row.get('country',row.get('nationality')),
                     specials=specials,specials_known=specials_known,available=row.get('available'),
                     value=_optional_num(field('value')),
                     salary_per_tour=_optional_num(field('salaryPerTour',current_contract.get('salaryPerTour'),
                         'contract.current' if 'salaryPerTour' in current_contract else None)),
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
                          'contract':contract or None,'formTrend':field('formTrend'),
                          'recentMatches':info.get('recentMatches'),
                          'profileStats':detail.get('stats'),
                          'source_values':{'roster':row,'detail':detail},
                          'field_provenance':provenance,'conflicts':conflicts,
                          'scouting':study,
                          'raw_style':info.get('style'),
                          'availability_status':'UNKNOWN' if p.available is None else ('AVAILABLE' if p.available else 'UNAVAILABLE'),
                          'style_label_is_not_verification':True}
        except (ValueError,TypeError) as exc:
            issues.append(f'{prefix}:invalid:{exc}')
    for sid in sorted(set(by_id)-seen):
        issues.append(f'orphan_player_details:{sid}')
    errors=[x for x in issues if ':invalid:' in x or 'missing_id_name_age_strength_or_position' in x]
    return {'players':players,'issues':issues,'accepted':len(players),'rejected':len(rows)-len(players),'total':len(rows),
            'error_count':len(errors),'warning_count':len(issues)-len(errors),
            'evidence_by_id':evidence,
            'note':'Normalized observations; text style labels do not prove study; no inferred availability'}
