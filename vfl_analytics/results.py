"""Explicit certainty contract; no implicit numeric coercion."""
from dataclasses import asdict, dataclass
from enum import Enum
from math import isfinite
from .validation import number


class ResultStatus(str, Enum):
    EXACT = "EXACT"
    BOUNDED = "BOUNDED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class CalculationResult:
    status: ResultStatus
    value: float | int | None = None
    lower: float | int | None = None
    upper: float | int | None = None
    unit: str = "fraction"
    source: str = ""
    reason: str = ""

    def __post_init__(self):
        object.__setattr__(self, "status", ResultStatus(self.status))
        if any(not isinstance(x,str) for x in (self.unit,self.source,self.reason)):
            raise ValueError('Result unit/source/reason must be strings')
        for value in (self.value, self.lower, self.upper):
            if value is not None:
                number(value,'result')
        if self.status in (ResultStatus.EXACT, ResultStatus.ESTIMATED):
            if self.value is None or self.lower is not None or self.upper is not None:
                raise ValueError("Point results require only value")
        elif self.status == ResultStatus.BOUNDED:
            if self.value is not None or self.lower is None or self.upper is None or self.lower > self.upper:
                raise ValueError("BOUNDED requires ordered bounds and no point value")
        elif any(x is not None for x in (self.value, self.lower, self.upper)):
            raise ValueError("Unknown/inapplicable results cannot contain numbers")

    def to_dict(self) -> dict:
        return {**asdict(self), "status": self.status.value}


def exact(value, *, unit="fraction", source="", reason=""):
    return CalculationResult(ResultStatus.EXACT, value=value, unit=unit, source=source, reason=reason)


def bounded(lower, upper, *, unit="fraction", source="", reason=""):
    if lower == upper:
        return exact(lower, unit=unit, source=source, reason=reason)
    return CalculationResult(ResultStatus.BOUNDED, lower=lower, upper=upper,
                             unit=unit, source=source, reason=reason)


def unknown(*, unit="fraction", source="", reason=""):
    return CalculationResult(ResultStatus.UNKNOWN, unit=unit, source=source, reason=reason)
