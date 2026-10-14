import json
from pathlib import Path
from copy import deepcopy
import pytest
from vfl_analytics import reporting
from vfl_analytics.local_validation import validate_directory
from vfl_analytics.snapshots import merge_team_snapshots
from test_observed_contracts import fixture

pytestmark=pytest.mark.synthetic


def setup_data(tmp_path,monkeypatch):
    root=tmp_path/'trusted';root.mkdir();monkeypatch.setattr(reporting,'LOCAL_DATA_ROOT',root)
    source=tmp_path/'inputs';source.mkdir()
    for sid in ('13202','22931','748'):
        for mode in ('normal','deep'):
            d=fixture('own_'+mode);d['teamId']=sid
            (source/(sid+'_'+mode+'.json')).write_text(json.dumps(d),encoding='utf8')
    return source,root


def test_multi_team_isolation_and_filter(tmp_path,monkeypatch):
    source,root=setup_data(tmp_path,monkeypatch)
    result=validate_directory(source,root/'summary')
    assert {t['team_id'] for t in result['teams'].values()}=={'13202','22931','748'}
    assert all(t['join']['accepted']==3 and len(t['source_ids'])==2 for t in result['teams'].values())
    result=validate_directory(source,root/'filtered',team_ids=['13202'])
    assert set(result['teams'])=={'own'} and len(result['inventory'])==2
    assert result['teams']['own']['team_id']=='13202'


def test_summary_detailed_raw_levels_and_hashes(tmp_path,monkeypatch):
    source,root=setup_data(tmp_path,monkeypatch)
    summary=validate_directory(source,root/'summary',team_ids=['13202'])
    serialized=json.dumps(summary,allow_nan=False)
    for forbidden in ('playerDetails','source_values','recentMatches','finances'):
        # Inventory/preservation section names are allowed, but no raw objects.
        assert ('"'+forbidden+'": {') not in serialized and ('"'+forbidden+'": [') not in serialized
    assert not (root/'summary'/'details.json').exists()
    assert not (root/'summary'/'raw_diagnostics.json').exists()
    assert all(e['snapshot_id']=='sha256:'+e['sha256'] and len(e['sha256'])==64 for e in summary['inventory'])
    full=validate_directory(source,root/'full',team_ids=['13202'],detailed=True,raw_diagnostics=True)
    assert (root/'full'/'details.json').exists() and (root/'full'/'raw_diagnostics.json').exists()
    details=json.loads((root/'full'/'details.json').read_text(encoding='utf8'))
    assert len(details['teams']['own']['players'])==3
    assert len((root/'summary'/'validation.json').read_bytes())<len((root/'full'/'details.json').read_bytes())
    assert set(full['teams']['own']['styles'])=={'normal','bb','british','catenaccio','spartak','brazil','tiki'}
    assert summary==validate_directory(source,root/'summary',team_ids=['13202'])


@pytest.mark.parametrize('suffix',['outside/local_data/report','local_data_fake/report','outside'])
def test_output_requires_real_trusted_ancestry(tmp_path,monkeypatch,suffix):
    source,root=setup_data(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='local_data'):
        validate_directory(source,tmp_path/suffix)
    with pytest.raises(ValueError):validate_directory(source,root/'..'/'escape')


def test_resolved_symlink_escape_is_rejected(tmp_path,monkeypatch):
    source,root=setup_data(tmp_path,monkeypatch)
    outside=tmp_path/'outside';outside.mkdir();link=root/'link'
    try:link.symlink_to(outside,target_is_directory=True)
    except OSError:
        # Windows without symlink privilege: emulate resolution to test the guard.
        original=Path.resolve
        monkeypatch.setattr(Path,'resolve',lambda self,*a,**kw:outside/'report' if self==link/'report' else original(self,*a,**kw))
    with pytest.raises(ValueError):validate_directory(source,link/'report')


def test_season_isolation_and_merge_rejection(tmp_path,monkeypatch):
    source,root=setup_data(tmp_path,monkeypatch)
    a=fixture('own_normal');b=fixture('own_deep');b['rosterSeasonStats']['scope']['season']=80
    with pytest.raises(ValueError,match='season'):merge_team_snapshots([a,b])
    a['teamId']='13202';b['teamId']='13202'
    for name,d in [('13202_normal',a),('13202_deep',b)]:
        (source/(name+'.json')).write_text(json.dumps(d),encoding='utf8')
    result=validate_directory(source,root/'seasons',team_ids=['13202'])
    assert len(result['teams'])==2
    assert {t['season'] for t in result['teams'].values()}=={79,80}


def test_same_id_own_opponent_are_separate(tmp_path,monkeypatch):
    source,root=setup_data(tmp_path,monkeypatch)
    d=fixture('opponent_deep');d['opponentId']='13202'
    (source/'opponent.json').write_text(json.dumps(d),encoding='utf8')
    result=validate_directory(source,root/'roles',team_ids=['13202'])
    assert set(result['teams'])=={'own','opponent'}
    assert result['teams']['own']['availability']['known_form']==3
    assert result['teams']['opponent']['availability']['known_form']==0
