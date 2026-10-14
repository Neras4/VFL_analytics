from copy import deepcopy
import json
import pytest
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.snapshots import merge_team_snapshots
from test_observed_contracts import fixture


def opponent(roster=None,profile=12,omit=False):
    d=fixture('opponent_deep');d['roster']['players']=d['roster']['players'][:1];d['playerDetails']=d['playerDetails'][:1]
    row=d['roster']['players'][0];row['fatigue']=roster
    d['playerDetails'][0]['fatigue']=roster;d['playerDetails'][0]['info']['fatigue']=profile
    if omit:row.pop('fatigue')
    return d


@pytest.mark.synthetic
@pytest.mark.parametrize('roster,profile,omit,expected',[(None,12,False,12),(10,12,False,10),(0,12,False,0),
    (None,None,False,None),(None,12,True,12)])
def test_fatigue_priority(roster,profile,omit,expected):
    r=adapt_roster(opponent(roster,profile,omit))
    assert r['players'][0].fatigue==expected
    e=r['evidence_by_id']['100']['field_provenance']['fatigue']
    assert e['value']==expected and e['reason'] and e['confidence']
    assert 'observation_time' in e and 'collection_reference' in e
    if expected is not None:assert e['source']==('roster' if roster is not None else 'playerDetails.info')


@pytest.mark.synthetic
def test_fatigue_no_profile_stale_and_unresolved():
    d=opponent();d['playerDetails']=[]
    assert adapt_roster(d)['players'][0].fatigue is None
    d=opponent();d['playerDetails'][0]['info']['collectedAt']='2026-10-13T15:00:00Z'
    assert adapt_roster(d)['players'][0].fatigue is None
    d=opponent();d['playerDetails'][0]['fatigue']=11
    assert adapt_roster(d)['players'][0].fatigue is None
    d=opponent(10,12);d['roster']['players'][0]['collectedAt']='2026-10-14T15:00:00Z'
    d['playerDetails'][0]['info']['collectedAt']='2026-10-14T15:01:00Z'
    assert adapt_roster(d)['players'][0].fatigue is None


@pytest.mark.synthetic
def test_old_deep_cannot_fill_new_normal_null():
    d=opponent();n=fixture('opponent_normal');n['generatedAt']='2026-10-15T15:00:00Z'
    out=adapt_roster(merge_team_snapshots([d,n])['snapshot'])
    assert out['players'][0].fatigue is None
    assert 'older collection' in out['evidence_by_id']['100']['field_provenance']['fatigue']['reason']


@pytest.mark.synthetic
def test_unsupported_collector_null_is_not_general_fallback():
    d=opponent();d['exporterVersion']='0.5.12'
    assert adapt_roster(d)['players'][0].fatigue is None


@pytest.mark.observed
def test_observed_completed_style_history():
    out=adapt_roster(fixture('scouting_style'));p=out['players'][0]
    assert p.style_known_percent==100 and p.favorite_style_is_known and p.favorite_style_verified
    assert p.favorite_style=='spartak'
    study=out['evidence_by_id']['104']['scouting']
    assert study['date']=='2026-10-05' and study['season']==79
    assert [r['level'] for r in study['history']]==[4,5]
    assert not any('missing_style_study' in s for s in out['issues'])
    json.dumps(out['evidence_by_id'],allow_nan=False)


@pytest.mark.synthetic
@pytest.mark.parametrize('change',['other_player','other_type','future','other_season','bad_date','bad_level','rollback','same_day_conflict','profile_conflict'])
def test_scouting_edge_cases(change):
    d=fixture('scouting_style');s=d['management']['scouting'];rows=s['completed'];style=[r for r in rows if r['studyType']=='стиль']
    if change=='other_player':
        for r in style:r['playerId']='999'
    if change=='other_type':
        for r in style:r['studyType']='рост силы'
    if change=='future':
        for r in style:r['date']='2026-10-20'
    if change=='other_season':s['season']=78
    if change=='bad_date':
        for r in style:r['date']='n/a'
    if change=='bad_level':
        for r in style:r['result']['level']=True
    if change=='rollback':style[0]['date']='2026-09-28'
    if change=='same_day_conflict':style[1]['date']=style[0]['date']
    if change=='profile_conflict':style[0]['result']['style']='brazil'
    p=adapt_roster(d)['players'][0]
    assert not p.favorite_style_is_known and p.style_known_percent is None


@pytest.mark.synthetic
def test_partial_study_not_sum_or_full_style():
    d=fixture('scouting_style');s=d['management']['scouting'];s['completed']=[r for r in s['completed'] if r['result']['level']==4]
    p=adapt_roster(d)['players'][0]
    assert p.style_known_percent==80 and not p.favorite_style_is_known


@pytest.mark.synthetic
def test_numeric_profile_time_is_not_invented():
    out=adapt_roster(opponent())
    e=out['evidence_by_id']['100']['field_provenance']['fatigue']
    assert e['observation_time'] is None and e['collection_reference']
