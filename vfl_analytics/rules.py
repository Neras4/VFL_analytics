"""Published components: official management page 40 v19.2 and season page 70 v14.0.
Sections 2.5, 2.8, 2.10, 2.11, 2.12, 2.13 and season aging.
No undisclosed generator parameters are inferred here.
"""
from __future__ import annotations
from dataclasses import dataclass
from .models import Player, style_id
from .arithmetic import round_usefulness, validate_age
from .results import CalculationResult, ResultStatus, exact, bounded
from .validation import number
from .rule_data import _data

MATCH_SOURCE = "https://vfliga.com/rules.php?page=40 §2.10–2.12, version 19.2"

# Winner -> style beaten. Exact directed cycle from section 2.11.
_CORE=_data('core.json')
_STYLES=('normal','bb','british','catenaccio','spartak','brazil','tiki')
COLLISION_WINS={_STYLES[i]:_STYLES[row.index(1)] for i,row in enumerate(_CORE['collision_outcomes']['cells']) if 1 in row}
STYLE_KNOWN_BONUS={int(k):v/100 for k,v in _CORE['style_study_match_bonus_pct'].items()}
YOUTH_THRESHOLDS={int(k):tuple(v) for k,v in _CORE['youth_growth_threshold_percent_by_age'].items()}
VETERAN_AGING_PERCENT={int(k):int(v*100) for k,v in _CORE['veteran_loss_fraction_by_age'].items()}


def collision(our_style: str, their_style: str) -> int:
    """+1 our win, -1 their win, 0 no collision. No invented size."""
    a, b = style_id(our_style), style_id(their_style)
    if a is None or b is None:
        raise ValueError('Both collision styles must be provided')
    if COLLISION_WINS.get(a) == b:
        return 1
    if COLLISION_WINS.get(b) == a:
        return -1
    return 0


def style_effect(p: Player, style: str) -> CalculationResult:
    """Incomplete study labels do not confirm an actual favorite style."""
    s = style_id(style)
    if s is None:
        raise ValueError('Chosen team style required')
    if s == "normal" or p.is_league_player:
        return exact(1., source=MATCH_SOURCE)
    if not p.favorite_style_is_known:
        maximum = STYLE_KNOWN_BONUS.get(p.style_known_percent, .025)
        return bounded(.99, 1. + maximum, source=MATCH_SOURCE,
                       reason="Actual favorite style or study percentage is not fully known")
    if p.favorite_style == s:
        if p.style_known_percent is None:
            return bounded(1., 1.025, source=MATCH_SOURCE, reason="Favorite verified; study percentage missing")
        return exact(1. + STYLE_KNOWN_BONUS[p.style_known_percent], source=MATCH_SOURCE)
    # Player-style vs team-style collision is -1%, independent of style knowledge.
    if collision(p.favorite_style, s):
        return exact(.99, source=MATCH_SOURCE)
    return exact(1., source=MATCH_SOURCE)


def baseline_strength(p: Player, our_style: str, pos_factor: float = 1.0) -> tuple[float | None, list[str]]:
    """A comparable *partial* prematch strength, not generator's exact output.
    Provisional multiplicative combination for form/fatigue/known style.
    """
    missing = []
    number(pos_factor,'position factor',positive=True)
    if p.fatigue is None:
        missing.append("fatigue")
    if p.form is None:
        missing.append("form")
    if missing:
        return None, missing
    effect = style_effect(p, our_style)
    if effect.status != ResultStatus.EXACT:
        missing.append("favorite_style_not_fully_known")
        return None, missing
    return p.strength * p.form / 100 * (1 - p.fatigue / 100) * effect.value * pos_factor, missing


def partial_strength_range(p: Player, our_style: str, pos_factor: float = 1.):
    """Range conditional on the legacy provisional product, never generator force."""
    number(pos_factor,'position factor',positive=True)
    if p.form is None or p.fatigue is None:
        from .results import unknown
        return unknown(unit='partial_strength_units',source=MATCH_SOURCE,reason='Form/fatigue missing')
    base=p.strength*p.form/100*(1-p.fatigue/100)*pos_factor
    effect=style_effect(p,our_style)
    if effect.status==ResultStatus.EXACT:
        return CalculationResult(ResultStatus.ESTIMATED,value=base*effect.value,
            unit='partial_strength_units',source=MATCH_SOURCE,reason='Provisional component product; published combination order unresolved')
    return bounded(base*effect.lower,base*effect.upper,unit='partial_strength_units',source=MATCH_SOURCE,
                   reason='Bounds conditional on provisional product, not full match force')


def captain_age_factor(age: int) -> float:
    """Rule 2.8 (without special Ка). Positive = fraction of captain force per other player.
    Negative = own force penalty fraction per other player.
    """
    from .abilities import captain_coefficient
    return captain_coefficient(age,0).value


def captain_bonus(captain: Player, strengths: dict[str, float]) -> float:
    """Total additive strength from captain age rule only (Ка requires separate model).
    Source says positive bonus ineffective if captain weaker than on-field mean.
    """
    if captain.id not in strengths or len(strengths) < 2:
        raise ValueError("captain not in lineup")
    for value in strengths.values():
        number(value,'captain force base',minimum=0)
    if any(s.lower().startswith("ка") for s in captain.specials):
        raise ValueError("Ka special effect not implemented; do not apply age-only captain model")
    coeff = captain_age_factor(captain.age)
    if coeff > 0 and strengths[captain.id] < sum(strengths.values())/len(strengths):
        return 0.0
    if coeff >= 0:
        return coeff * strengths[captain.id] * (len(strengths)-1)
    return coeff * (sum(strengths.values()) - strengths[captain.id])


def line_chemistry(receiver: Player | None, other: Player | None) -> CalculationResult:
    """Published directed bounds over all styles compatible with evidence.

    Partial study does not confirm a singleton label. Missing nationality
    allows both same/different cases. No statistical assumption is used.
    """
    if receiver is None or other is None or receiver.is_league_player or other.is_league_player:
        return exact(0., source=MATCH_SOURCE, reason="Empty or League endpoint; line still counts")
    styles = tuple(COLLISION_WINS)
    a_styles = (receiver.favorite_style,) if receiver.favorite_style_is_known else styles
    b_styles = (other.favorite_style,) if other.favorite_style_is_known else styles
    studies = (other.style_known_percent,) if other.style_known_percent is not None else tuple(STYLE_KNOWN_BONUS)
    nations = (receiver.nationality == other.nationality,) if receiver.nationality and other.nationality else (False, True)
    possible = []
    for a in a_styles:
        for b in b_styles:
            for study in studies:
                raw = .125 * study / 100 if a == b else (-.05 if collision(a, b) else 0.)
                for same_nation in nations:
                    possible.append(max(.05, raw) if same_nation else raw)
    return bounded(min(possible), max(possible), source=MATCH_SOURCE,
                   reason="Published component; interval when style/study/nationality evidence is incomplete")


def chemistry_for_player(receiver: Player | None, neighbours: list[Player | None]) -> tuple[CalculationResult, int]:
    """Average bounds; zero endpoints remain in the line denominator."""
    if not neighbours:
        return CalculationResult(ResultStatus.NOT_APPLICABLE, source=MATCH_SOURCE,
                                 reason="No incident lines"), 0
    effects = [line_chemistry(receiver, p) for p in neighbours]
    uncertain = sum(x.status != ResultStatus.EXACT for x in effects)
    low = sum(x.value if x.status == ResultStatus.EXACT else x.lower for x in effects) / len(effects)
    high = sum(x.value if x.status == ResultStatus.EXACT else x.upper for x in effects) / len(effects)
    return bounded(low, high, source=MATCH_SOURCE, reason="Mean of incident line bounds"), uncertain


def defense_choice(opponent_attack_count: int | None) -> str | None:
    if opponent_attack_count is None:
        return None
    number(opponent_attack_count,'opponent_attack_count',minimum=0,integer=True)
    return "zonal" if opponent_attack_count > 3 else "personal"


def youth_growth(age: int, minutes_pct: float) -> int:
    """Exact points from age-specific minimum useful-time thresholds."""
    validate_age(age)
    rounded = round_usefulness(minutes_pct)
    return sum(rounded >= x for x in YOUTH_THRESHOLDS.get(age, ()))


def veteran_useful(minutes_pct: float) -> bool:
    return round_usefulness(minutes_pct) >= 55
