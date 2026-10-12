import json,subprocess,sys
from dataclasses import replace
from pathlib import Path
import pytest
from vfl_analytics.adapters import adapt_roster
from vfl_analytics.models import Player,PositionPlan
from vfl_analytics.lineup import optimize_lineups
from vfl_analytics.results import ResultStatus
from vfl_analytics.abilities import ability_components,ability_lookup,penalty_bonus
from vfl_analytics.rule_data import _data,_manifest,RuleDataError
from test_models import roster,SLOTS

pytestmark=pytest.mark.synthetic


@pytest.mark.parametrize('form',[74,126,300])
def test_form_domain_is_published_not_generic_percentage(form):
    with pytest.raises(ValueError): replace(roster()[0],form=form)


def test_absent_specials_and_bare_collector_levels():
    row={'id':'10','name':'A','position':'CM','age':20,'strength':100}
    result=adapt_roster({'players':[row]})
    assert result['players'][0].specials_known is False
    row['specials']=['Ка','Ат']
    result=adapt_roster({'players':[row]})
    assert result['players'][0].specials==('Ка1','Ат1')
    assert result['players'][0].specials_known is True


def test_special_profile_restrictions():
    with pytest.raises(ValueError): replace(roster()[0],specials=('У4',))
    out=ability_components('Р',4,native_positions=('CM',))
    assert out['result']['status']=='NOT_APPLICABLE'


def test_lookup_units_distinguish_fraction_multiplier_and_probability():
    assert ability_lookup('Тр',4,'injury_incidence_multiplier','levels0to4').unit=='multiplier'
    assert ability_lookup('См',4,'defensive_card_probability','by_level').unit=='relative_probability_change'
    assert penalty_bonus(100,1,4,[{'level':4,'strength':None}],strength_basis_verified=True).status==ResultStatus.UNKNOWN


def test_missing_player_stats_preserve_feasibility_but_not_eligibility_claim():
    ps=[replace(p,fatigue=None,form=None,favorite_style=None,style_known_percent=None) for p in roster()]
    result=optimize_lineups(ps,[PositionPlan(SLOTS)],styles=['spartak'])
    assert result['results']
    assert result['results'][0]['partial_total'] is None
    assert result['results'][0]['lineup_eligibility']['status']=='UNKNOWN'
    assert result['results'][0]['partial_model_range']['status']=='UNKNOWN'


def test_corrupted_packaged_table_checksum_is_rejected(monkeypatch):
    import vfl_analytics.rule_data as module
    class File:
        def joinpath(self,path): return self
        def read_bytes(self): return b'corrupted'
    _manifest()  # Keep verified manifest before redirecting resource bytes.
    _data.cache_clear()
    monkeypatch.setattr(module,'files',lambda name:File())
    try:
        with pytest.raises(RuleDataError,match='checksum'):
            _data('weather.json.gz')
    finally:
        _data.cache_clear()


@pytest.mark.parametrize('raw',['[]','{"action":"collision","our_style":NaN,"their_style":"bb"}'])
def test_cli_invalid_json_returns_structured_error(tmp_path,raw):
    path=tmp_path/'invalid.json'; path.write_text(raw,encoding='utf8')
    result=subprocess.run([sys.executable,'-m','vfl_analytics.cli',str(path)],capture_output=True,text=True,encoding='utf8')
    assert result.returncode==2
    assert json.loads(result.stderr)['error']=='ValueError'
