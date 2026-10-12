"""Stable calculation input; keep collector schema out of the mathematical core."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
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
    key = str(value).strip().casefold()
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
        if not self.id or not self.name:
            raise ValueError("Player needs id and name")
        validate_age(self.age)
        if self.strength <= 0:
            raise ValueError(f"Invalid age/strength for {self.name}")
        if self.form is not None and not (1 <= self.form <= 300):
            raise ValueError("form is a percentage such as 112, not a fraction")
        if self.fatigue is not None and not (0 <= self.fatigue <= 100):
            raise ValueError("fatigue must be 0..100")
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
        positions = tuple(p.strip().upper() for p in self.positions)
        if not positions:
            raise ValueError("positions required")
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
        if self.opponent_strength_ratio is not None and self.opponent_strength_ratio <= 0:
            raise ValueError("opponent_strength_ratio must be positive")
        if self.attack_count is not None and self.attack_count < 0:
            raise ValueError("attack_count must be non-negative")


@dataclass(frozen=True)
class PositionPlan:
    slots: tuple[str, ...]
    # For a given *our* team style, externally verified slot effects.
    style_position_multipliers: dict[str, dict[str, float]] = field(default_factory=dict)
    # A link is between slot IDs (e.g. CM1 -> DM), NOT players. May be empty.
    links: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if len(self.slots) != 11 or sum(s.startswith("GK") for s in self.slots) != 1:
            raise ValueError("Exactly 11 slots including one GK required")
        if len(set(self.slots)) != 11:
            raise ValueError("Slot names must be distinct, e.g. CD1, CD2")
        for style, factors in self.style_position_multipliers.items():
            style_id(style)
            if any(not (0 < x <= 2) for x in factors.values()):
                raise ValueError("Position factors must be positive multipliers")


def base_position(slot: str) -> str:
    return slot.rstrip("0123456789").upper()
