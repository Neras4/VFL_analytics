"""Exact rational boundaries for nonnegative decimal inputs, without float ties."""
from fractions import Fraction

SEASON_SOURCE = "https://www.vfliga.com/rules.php?page=70 §2–3, version 14.0"


def nonnegative(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite nonnegative number")
    try:
        number = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"{name} must be a finite nonnegative number") from None
    if number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def integral_minutes(value, name):
    number = nonnegative(value, name)
    if number.denominator != 1:
        raise ValueError(f"{name} must be integral minutes")
    return number.numerator


def round_usefulness(percent) -> int:
    number = nonnegative(percent, "percent")
    return (2 * number.numerator + number.denominator) // (2 * number.denominator)


def validate_age(age):
    if isinstance(age, bool) or not isinstance(age, int) or not 16 <= age <= 34:
        raise ValueError("Age must be an integer in 16..34")
