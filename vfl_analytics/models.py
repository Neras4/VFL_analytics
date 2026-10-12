"""Stable calculation input; keep collector schema out of the mathematical core."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from datetime import date
from .validation import number, identity, positions as validate_positions, special_list, NATIVE_POSITIONS, SPECIAL_POSITIONS
from .arithmetic import validate_age


class StyleKnowledge(str, Enum):
    FULLY_KNOWN = "FULLY_KNOWN"
    PARTIALLY_STUDIED = "PARTIALLY_STUDIED"
    UNKNOWN = "UNKNOWN"
    MISSING = "MISSING"

STYLE_NAMES = ("normal", "bb", "british", "catenaccio", "spartak", "brazil", "tiki")
STYLE_ALIASES = {
    "normal": "normal", "нормальный": "normal", "норма": "normal",
    "bb": "bb", "бей-беги": "bb", "бей беги": "bb", "kick-and-rush": "bb",
    "british": "british", "британский": "british", "британь": "british",
    "catenaccio": "catenaccio", "катеначчо": "catenaccio", "катя": "catenaccio",
    "spartak": "spartak", "спартаковский": "spartak", "спартак": "spartak",
    "brazil": "brazil", "бразильский": "brazil", "бразилия": "brazil",
    "tiki": "tiki", "тики-така": "tiki", "тики така": "tiki",
}


def style_id(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value,str):
        raise ValueError('Style must be a supported string or null')
    key = value.strip().casefold()
    if key not in STYLE_ALIASES:
        raise ValueError(f"Unknown style: {value!r}; use supported names")
    return STYLE_ALIASES[key]


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    positions: tuple[str, ...]
    age: int
    strength: float
    fatigue: float | None = None  # 0..100 percent
    form: float | None = None  # e.g. 112 means 112%; NOT 1.12
    real_strength: float | None = None  # VFL collector diagnostic, not multiplied twice
    favorite_style: str | None = None
    style_known_percent: int | None = None  # None means absent evidence, not 0
    nationality: str | None = None
    specials: tuple[str, ...] = ()
    available: bool | None = None  # None = not checked; only False is confirmed unavailable
    value: float | None = None
    salary_per_tour: float | None = None
    played_minutes: float | None = None
    is_league_player: bool = False
    favorite_style_verified: bool = False  # Explicit independent evidence, never inferred from text.

    @property
    def favorite_style_is_known(self) -> bool:
        return self.favorite_style is not None and (self.style_known_percent == 100 or self.favorite_style_verified)

    @property
    def style_knowledge(self) -> StyleKnowledge:
        if self.style_known_percent is None:
            return StyleKnowledge.MISSING
        if self.style_known_percent == 100 and self.favorite_style is not None:
            return StyleKnowledge.FULLY_KNOWN
        if self.style_known_percent in (20, 40, 60, 80):
            return StyleKnowledge.PARTIALLY_STUDIED
        return StyleKnowledge.UNKNOWN

    def __post_init__(self):
        identity(self.id)
        if not isinstance(self.name,str) or not self.name.strip():
            raise ValueError("Player needs id and name")
        validate_age(self.age)
        number(self.strength,'strength',positive=True)
        for name,value,lo,hi in [('form',self.form,1,300),('fatigue',self.fatigue,0,100),
                ('real_strength',self.real_strength,0,None),('value',self.value,0,None),
                ('salary_per_tour',self.salary_per_tour,0,None)]:
            if value is not None:
                number(value,name,minimum=lo,maximum=hi)
        if self.played_minutes is not None:
            number(self.played_minutes,'played_minutes',minimum=0,integer=True)
        if self.available is not None and not isinstance(self.available,bool):
            raise ValueError('available must be boolean or null')
        if self.nationality is not None and (not isinstance(self.nationality,str) or not self.nationality.strip()):
            raise ValueError('nationality must be a nonempty string or null')
        special_list(self.specials)
        if self.style_known_percent is not None and (isinstance(self.style_known_percent, bool)
                or not isinstance(self.style_known_percent, int)
                or self.style_known_percent not in (0, 20, 40, 60, 80, 100)):
            raise ValueError("style_known_percent must be null or 0/20/40/60/80/100")
        if not isinstance(self.is_league_player, bool):
            raise ValueError("is_league_player must be boolean")
        if not isinstance(self.favorite_style_verified, bool):
            raise ValueError("favorite_style_verified must be boolean")
        style = style_id(self.favorite_style)
        if style == "normal":
            raise ValueError("normal is not a player favorite style")
        object.__setattr__(self, "favorite_style", style)
        positions = validate_positions(self.positions)
        object.__setattr__(self, "positions", positions)


@dataclass(frozen=True)
class MatchObservation:
    style: str
    date: str  # YYYY-MM-DD; observations strictly before target date
    home: bool | None = None
    opponent_strength_ratio: float | None = None  # adversary / observed team
    formation: str | None = None
    attack_count: int | None = None
    competition: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "style", style_id(self.style))
        if self.style is None:
            raise ValueError('Observation style required')
        try:
            date.fromisoformat(self.date)
        except (ValueError,TypeError):
            raise ValueError('Invalid observation date') from None
        if self.home is not None and not isinstance(self.home,bool):
            raise ValueError('home must be boolean or null')
        if self.opponent_strength_ratio is not None:
            number(self.opponent_strength_ratio,'opponent_strength_ratio',positive=True)
        if self.attack_count is not None:
            number(self.attack_count,'attack_count',minimum=0,integer=True)


@dataclass(frozen=True)
class PositionPlan:
    slots: tuple[str, ...]
    # For a given *our* team style, externally verified slot effects.
    style_position_multipliers: dict[str, dict[str, float]] = field(default_factory=dict)
    # A link is between slot IDs (e.g. CM1 -> DM), NOT players. May be empty.
    links: tuple[tuple[str, str], ...] = ()
    defense_formation: str | None = None  # 'line' or 'sweeper'; explicit tactical context.

    def __post_init__(self):
        if not isinstance(self.slots,(tuple,list)) or any(not isinstance(s,str) for s in self.slots):
            raise ValueError('slots must be strings')
        if any(base_position(s) not in NATIVE_POSITIONS | SPECIAL_POSITIONS for s in self.slots):
            raise ValueError('Unknown tactical slot')
        if len(self.slots) != 11 or sum(base_position(s)=='GK' for s in self.slots) != 1:
            raise ValueError("Exactly 11 slots including one GK required")
        if len(set(self.slots)) != 11:
            raise ValueError("Slot names must be distinct, e.g. CD1, CD2")
        for style, factors in self.style_position_multipliers.items():
            style_id(style)
            if not isinstance(factors,dict):
                raise ValueError('Position factors must be mappings')
            for slot,x in factors.items():
                if slot not in self.slots and slot not in NATIVE_POSITIONS | SPECIAL_POSITIONS:
                    raise ValueError('Factor for unknown slot')
                number(x,'position factor',positive=True,maximum=2)
        if self.defense_formation not in (None,'line','sweeper'):
            raise ValueError('Unknown defense formation')
        if self.defense_formation=='line' and any(base_position(s)=='SW' for s in self.slots):
            raise ValueError('SW conflicts with defense line')
        for link in self.links:
            if len(link)!=2 or link[0] not in self.slots or link[1] not in self.slots or link[0]==link[1]:
                raise ValueError('Invalid chemistry link')
        if len({frozenset(x) for x in self.links})!=len(self.links):
            raise ValueError('Duplicate chemistry link')


def base_position(slot: str) -> str:
    return slot.rstrip("0123456789").upper()
