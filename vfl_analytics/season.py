"""Published usefulness boundaries; forecasts conditional on a denominator scenario."""
from fractions import Fraction
from .arithmetic import SEASON_SOURCE, integral_minutes, nonnegative, round_usefulness, validate_age
from .results import CalculationResult, ResultStatus, exact, unknown
from .rules import YOUTH_THRESHOLDS, youth_growth, veteran_useful, VETERAN_AGING_PERCENT


def usefulness(player_minutes, team_minutes) -> CalculationResult:
    if player_minutes is None or team_minutes is None:
        for name, value in (("player_minutes", player_minutes), ("team_minutes", team_minutes)):
            if value is not None:
                integral_minutes(value, name)
        return unknown(unit="percent", source=SEASON_SOURCE, reason="Missing numerator or denominator")
    played = integral_minutes(player_minutes, "player_minutes")
    team = integral_minutes(team_minutes, "team_minutes")
    if team == 0:
        return unknown(unit="percent", source=SEASON_SOURCE, reason="Zero denominator")
    return exact(round_usefulness(Fraction(100 * played, team)), unit="percent", source=SEASON_SOURCE)


def minimum_target_minutes(threshold_pct, final_team_minutes) -> int:
    threshold = nonnegative(threshold_pct, "threshold_pct")
    if threshold.denominator != 1:
        raise ValueError("Threshold must be an integer percentage")
    team = integral_minutes(final_team_minutes, "final_team_minutes")
    if team == 0:
        raise ValueError("Final team denominator must be positive")
    boundary = max(Fraction(0), (threshold - Fraction(1, 2)) * team / 100)
    return -(-boundary.numerator // boundary.denominator)


def plan_usefulness(age: int, played_minutes, official_team_minutes,
                    future_official_team_minutes, target_growth: int | None = None,
                    *, available_future_player_minutes=None) -> dict:
    validate_age(age)
    played = integral_minutes(played_minutes, "played_minutes")
    team = integral_minutes(official_team_minutes, "official_team_minutes")
    future = None if future_official_team_minutes is None else integral_minutes(
        future_official_team_minutes, "future_official_team_minutes")
    budget = None if available_future_player_minutes is None else integral_minutes(
        available_future_player_minutes, "available_future_player_minutes")
    current = usefulness(played, team)
    final = None if future is None else team + future
    if final == 0:
        raise ValueError("Final team denominator must be positive")
    projected = usefulness(played, final)
    result = {"age": age, "current_pct": current.value,
              "current_usefulness": current.to_dict(),
              "projected_pct_no_more_play": projected.value,
              "projected_usefulness": projected.to_dict(),
              "final_team_minutes_scenario": final,
              "per_player_feasible": None,
              "limitation": "Conditional on final owner's team-minute scenario; calendar, availability, role and retirement are separate"}
    threshold = None
    if age in YOUTH_THRESHOLDS:
        thresholds = YOUTH_THRESHOLDS[age]
        goal = len(thresholds) if target_growth is None else target_growth
        if isinstance(goal, bool) or not isinstance(goal, int) or not 1 <= goal <= len(thresholds):
            raise ValueError("Requested youth growth is not achievable for this age")
        threshold = thresholds[goal - 1]
        result.update(target_growth=goal,
            currently_expected_growth_if_season_ended=None if current.value is None else youth_growth(age, current.value),
            projected_growth_no_more_play=None if projected.value is None else youth_growth(age, projected.value))
    elif age >= 30:
        threshold = 55
        result.update(veteran_currently_useful=None if current.value is None else veteran_useful(current.value),
            veteran_projected_useful=None if projected.value is None else veteran_useful(projected.value),
            veteran_age_decline_pct=VETERAN_AGING_PERCENT.get(age))
    else:
        result.update(target_growth=0, minimum_future_player_minutes=0,
                      target_minutes_result=CalculationResult(ResultStatus.NOT_APPLICABLE,
                          unit="minutes", source=SEASON_SOURCE, reason="No youth/veteran threshold at age 24-29").to_dict())
    if threshold is not None:
        target = None if final is None else minimum_target_minutes(threshold, final)
        required = None if target is None else max(0, target - played)
        result.update(threshold_pct=threshold, target_player_minutes=target,
                      minimum_future_player_minutes=required,
                      target_minutes_result=(unknown(unit="minutes", source=SEASON_SOURCE,
                          reason="Future team minutes scenario missing") if target is None else
                          exact(target, unit="minutes", source=SEASON_SOURCE,
                                reason="Exact arithmetic conditional on supplied scenario")).to_dict())
        if required is not None and budget is not None:
            result["per_player_feasible"] = required <= budget
            result["feasibility_basis"] = "Conditional on explicitly supplied playable-player-minute budget"
    return result
