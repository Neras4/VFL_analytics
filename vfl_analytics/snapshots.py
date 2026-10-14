"""Offline snapshot joins. Observations are ordered by collector time, never filename."""
from copy import deepcopy
from datetime import datetime
from .adapters import _id


def collection_time(value):
    if not isinstance(value, str):
        raise ValueError('Collection timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('Invalid collection timestamp') from None
    if result.tzinfo is None:
        raise ValueError('Collection timestamp must include timezone')
    return result


def snapshot_season(snapshot):
    """Current aggregate/management seasons only; selectedStats may be historic."""
    seasons=set()
    season=((snapshot.get('rosterSeasonStats') or {}).get('scope') or {}).get('season')
    if season is not None:seasons.add(season)
    management=snapshot.get('management') or {}
    for section in management.values() if isinstance(management,dict) else []:
        if isinstance(section,dict) and section.get('season') is not None:seasons.add(section['season'])
    if any(type(s) is not int or s<1 for s in seasons) or len(seasons)>1:
        raise ValueError('Conflicting or invalid current snapshot seasons')
    return next(iter(seasons),None)


def merge_team_snapshots(snapshots):
    """Latest roster defines membership/state; missing sections survive older snapshots.

    Lists other than playerDetails are whole observations, not unioned histories.
    Explicit null wins. Equal-time conflicting observations are rejected.
    """
    if not isinstance(snapshots, list) or not snapshots:
        raise ValueError('Nonempty snapshot list required')
    teams = set()
    ordered = []
    for i, snap in enumerate(snapshots):
        if not isinstance(snap, dict):
            raise ValueError('Snapshot must be object')
        kind = snap.get('kind')
        if kind not in ('vfl-own-team-context', 'vfl-opponent-context'):
            raise ValueError('Only team snapshots can be merged')
        from .validation import identity
        teams.add((kind, identity(snap.get('teamId', snap.get('opponentId')), collector=True)))
        ordered.append((collection_time(snap.get('generatedAt')), i, snap))
    if len(teams) != 1:
        raise ValueError('Cannot merge different teams or snapshot kinds')
    seasons={snapshot_season(s) for _,_,s in ordered}
    if len(seasons)>1:
        raise ValueError('Cannot merge incompatible or unverified different seasons')
    ordered.sort(key=lambda x: x[0])
    for a, b in zip(ordered, ordered[1:]):
        if a[0] == b[0] and a[2] != b[2]:
            raise ValueError('Conflicting snapshots at identical collection time')
    result = {}; provenance = {}; conflicts = []; diagnostics = []

    def overlay(target, incoming, path, source):
        for key, value in incoming.items():
            at = f'{path}.{key}' if path else key
            if isinstance(value, dict) and (key not in target or isinstance(target.get(key), dict)) and key not in ('rosterSeasonStats','selectedStats','scope'):
                target.setdefault(key,{})
                overlay(target[key], value, at, source)
                provenance[at]=source
            else:
                if key in target and target[key] != value:
                    conflicts.append({'path': at, 'previous_source': provenance.get(at),
                                      'selected_source': source, 'policy': 'latest_observation'})
                target[key] = deepcopy(value)
                provenance[at] = source

    details = {}
    sources = []
    for _, index, snap in ordered:
        source = {'input_index': index, 'generatedAt': snap['generatedAt'],
                  'snapshot_id':snap.get('_snapshot_id'),
                  'depth': snap.get('depth'), 'exporterVersion': snap.get('exporterVersion')}
        sources.append(source)
        overlay(result, {k:v for k,v in snap.items() if k not in ('playerDetails', 'roster')}, '', source)
        if 'roster' in snap:
            # Do not fill older state into an authoritative current roster.
            if 'roster' in result and result['roster'] != snap['roster']:
                conflicts.append({'path':'roster','previous_source':provenance.get('roster'),
                                  'selected_source':source,'policy':'latest_roster_observation'})
            result['roster']=deepcopy(snap['roster'])
            provenance['roster']=source
        rows = snap.get('playerDetails', [])
        if not isinstance(rows, list):
            raise ValueError('playerDetails must be list')
        counts = {}; valid = []
        for n, row in enumerate(rows):
            try:
                sid = _id(row); counts[sid] = counts.get(sid, 0) + 1; valid.append((sid,row))
            except (ValueError, TypeError, AttributeError):
                diagnostics.append(f'input[{index}].detail[{n}]:invalid_identity')
        for sid, row in valid:
            if counts[sid] > 1:
                details.pop(sid, None)
                diagnostics.append(f'input[{index}]:duplicate_details:{sid}')
                continue
            overlay(details.setdefault(sid, {}), row, f'playerDetails[{sid}]', source)
    result['playerDetails'] = list(details.values())
    result['_source_provenance']=deepcopy(provenance)
    return {'snapshot': result, 'provenance': provenance, 'conflicts': conflicts,
            'issues': diagnostics, 'sources': sources,
            'effective_sections':sorted(result),
            'policy': 'Latest roster membership/state including null; latest present section; details by stable ID'}
