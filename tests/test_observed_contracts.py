"""OBSERVED STRUCTURE, anonymized/minimized values; no generator validation."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.snapshots import merge_team_snapshots
from vfl_analytics.market_adapter import adapt_market_snapshot
from vfl_analytics.cli import run_request

ROOT=Path(__file__).parent/'fixtures'/'observed'


def fixture(name):
    return json.loads((ROOT/(name+'.json')).read_text(encoding='utf8'))


@pytest.mark.observed
@pytest.mark.parametrize('team,count',[('own',3),('opponent',3)])
def test_observed_join_preserves_sections_and_ids(team,count):
    normal,deep=fixture(team+'_normal'),fixture(team+'_deep')
    merged=merge_team_snapshots([deep,normal])
    out=adapt_roster(merged['snapshot'])
    assert out['accepted']==count and out['rejected']==out['error_count']==0
    assert {p.id for p in out['players']}=={'100','101','102'}
    assert len(merged['snapshot']['playerDetails'])==count
    assert merged==merge_team_snapshots([deep,normal])
    if team=='own':
        assert 'finances' in merged['snapshot'] and 'teamStatistics' in merged['snapshot']
        assert all(e['rosterSeasonStats'] for e in out['evidence_by_id'].values())
    else:
        # Review D: v0.5.11 gates roster fatigue on visible form; profile is independent.
        assert all(p.form is None and p.fatigue is not None and p.favorite_style is None for p in out['players'])
        assert not any('unverified_favorite_style' in x for x in out['issues'])
        assert all(e['raw_style']=='Неизвестно' for e in out['evidence_by_id'].values())


@pytest.mark.observed
def test_observed_scopes_and_style_label_are_not_verification():
    out=adapt_roster(fixture('own_deep'))
    assert all(p.style_known_percent is None and not p.favorite_style_is_known for p in out['players'])
    assert all(p.played_minutes is not None for p in out['players'])
    assert all(p.salary_per_tour==1000 for p in out['players'])
    for e in out['evidence_by_id'].values():
        assert e['selectedStats'] is not e['rosterSeasonStats']


@pytest.mark.observed
@pytest.mark.parametrize('name,count',[('market_0',0),('market_50',2),('market_38',2),('bids_0',0),('bids_1',1)])
def test_observed_market_boundary(name,count):
    out=adapt_market_snapshot(fixture(name))
    assert out['accepted']==count and out['rejected']==0
    assert out['roster_players']==[] and out['utility_model'] is None
    if name=='market_50':
        assert out['pagination']['totalResults']==63 and not out['complete']
        assert out['rows'][0]['form'] is None
        assert out['sort']['requested']=='strength' and out['sort']['applied'] is True
    if name=='market_38':
        assert out['sort']['requested']=='price' and out['sort']['applied'] is False
    if name=='bids_1':
        assert out['rows'][0]['bidPrice']==100000
        assert out['rows'][0]['observation']['bidType']=='active'
        assert out['purchase_limits']['GK']==1


@pytest.mark.observed
def test_observed_bid_states_independent():
    before,after=[adapt_market_snapshot(fixture(n)) for n in ('bids_0','bids_1')]
    assert before['generatedAt']<after['generatedAt']
    assert before['total_rows']==0 and after['total_rows']==1


@pytest.mark.observed
def test_observed_cli_merge_and_market_serializable():
    for request in [dict(action='merge_snapshots',snapshots=[fixture('own_normal'),fixture('own_deep')]),
                    dict(action='adapt_market',snapshot=fixture('market_50'))]:
        json.dumps(run_request(request),allow_nan=False)


@pytest.mark.synthetic
def test_conflict_latest_null_and_provenance():
    n,d=fixture('own_normal'),fixture('own_deep')
    d['roster']['players'][0]['fatigue']=None
    d['playerDetails'][0]['info']['fatigue']=9
    merged=merge_team_snapshots([n,d]);out=adapt_roster(merged['snapshot'])
    assert out['players'][0].fatigue is None
    assert merged['provenance']['roster']['generatedAt']==d['generatedAt']
    assert out['evidence_by_id']['100']['field_provenance']['fatigue']['source']=='roster'
    assert out['evidence_by_id']['100']['conflicts']


@pytest.mark.synthetic
@pytest.mark.parametrize('change',['other_team','other_kind','bad_time','equal_time'])
def test_merge_rejects_ambiguous_observations(change):
    a,b=fixture('own_normal'),fixture('own_deep')
    if change=='other_team':b['teamId']='9'
    if change=='other_kind':b['kind']='vfl-transfer-market'
    if change=='bad_time':b['generatedAt']='2026-10-14'
    if change=='equal_time':b['generatedAt']=a['generatedAt']
    with pytest.raises(ValueError):merge_team_snapshots([a,b])


@pytest.mark.synthetic
@pytest.mark.parametrize('mutation',['bad_row','bad_contract','duplicate','bad_special','nonfinite'])
def test_bad_player_is_localized(mutation):
    d=fixture('own_deep')
    if mutation=='bad_row':d['roster']['players'][0]=None
    if mutation=='bad_contract':d['playerDetails'][0]['contract']={'current':['bad']}
    if mutation=='duplicate':d['roster']['players'][0]=deepcopy(d['roster']['players'][1])
    if mutation=='bad_special':d['roster']['players'][0]['specials']=['bad4']
    if mutation=='nonfinite':d['roster']['players'][0]['strength']=float('nan')
    out=adapt_roster(d)
    assert out['accepted']==2 and out['rejected']==1 and out['error_count']>=1


@pytest.mark.synthetic
@pytest.mark.parametrize('key,value',[('form',True),('bidsCount',1.5),('bidPrice',-1),('specials','foo4'),('strength',float('inf'))])
def test_market_row_errors_local(key,value):
    d=fixture('bids_1');d['management']['transferMarket']['myBids']['bids'][0][key]=value
    out=adapt_market_snapshot(d)
    assert out['accepted']==0 and out['rejected']==1


@pytest.mark.synthetic
def test_latest_roster_does_not_resurrect_departed_players():
    a,b=fixture('own_normal'),fixture('own_deep')
    b['roster']['players']=b['roster']['players'][:1]
    out=adapt_roster(merge_team_snapshots([a,b])['snapshot'])
    assert out['total']==out['accepted']==1
    assert sum('orphan_player_details' in x for x in out['issues'])==2
