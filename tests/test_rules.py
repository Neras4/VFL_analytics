import pytest
pytestmark = pytest.mark.synthetic
from vfl_analytics.models import Player
from vfl_analytics.rules import (collision, baseline_strength, line_chemistry,
                                  captain_age_factor, captain_bonus, youth_growth,
                                  defense_choice)


def make(**kw):
    data=dict(id='1',name='A',positions=('CM',),age=30,strength=100,
              fatigue=10,form=110,favorite_style='spartak',style_known_percent=100,
              nationality='JP')
    data.update(kw)
    return Player(**data)


def test_collision_direction_exact_cycle():
    for a,b in [('bb','spartak'),('spartak','british'),('british','tiki'),
                ('tiki','catenaccio'),('catenaccio','brazil'),('brazil','bb')]:
        assert collision(a,b)==1
        assert collision(b,a)==-1
    assert collision('tiki','spartak')==0
    assert collision('normal','bb')==0


def test_known_strength_components():
    p=make()
    val,issues=baseline_strength(p,'spartak')
    assert val == pytest.approx(100*1.1*.9*1.025)
    assert not issues
    val,_=baseline_strength(p,'bb')
    assert val==pytest.approx(100*1.1*.9*.99)
    assert baseline_strength(make(fatigue=None),'spartak')[0] is None


def test_captain_age_rule_and_strength_gate():
    assert [captain_age_factor(a) for a in [16,23,24,25,26,27,28,29,30,31,32,33,34]] == pytest.approx(
        [-.08,-.01,0,0,.01,.01,.02,.03,.04,.05,.06,.07,.08])
    p=make(id='cap',age=33)
    assert captain_bonus(p,{'cap':110,'other':100})==pytest.approx(7.7)
    assert captain_bonus(p,{'cap':90,'other':100})==0
    p2=make(id='cap',age=19)
    assert captain_bonus(p2,{'cap':110,'other':100})==pytest.approx(-5.)
    with pytest.raises(ValueError):
        captain_bonus(make(id='cap',specials=('Ка4',)),{'cap':110,'other':100})


def test_chemistry_directed_and_same_nation_floor():
    a=make(id='a',favorite_style='spartak',nationality='JP')
    b=make(id='b',favorite_style='spartak',style_known_percent=20,nationality='BR')
    # Partial study no longer confirms the actual favorite style.
    assert (line_chemistry(a,b).lower,line_chemistry(a,b).upper)==pytest.approx((-.05,.025))
    assert (line_chemistry(b,a).lower,line_chemistry(b,a).upper)==pytest.approx((-.05,.125))
    assert line_chemistry(a,make(id='c',favorite_style='british',nationality='JP')).value==.05
    assert line_chemistry(a,make(id='d',favorite_style='bb',nationality='BR')).value==-.05
    uncertain=line_chemistry(a,make(id='e',favorite_style=None,nationality='BR'))
    assert uncertain.value is None
    assert (uncertain.lower,uncertain.upper)==(-.05,.125)


def test_growth_and_defense():
    assert youth_growth(16,19.9)==10  # Published half-up rounding before thresholds.
    assert youth_growth(16,20)==10
    assert youth_growth(17,28)==9
    assert youth_growth(18,38)==8
    assert youth_growth(19,44)==7
    assert youth_growth(24,100)==0
    assert defense_choice(4)=='zonal'
    assert defense_choice(3)=='personal'
    assert defense_choice(None) is None
