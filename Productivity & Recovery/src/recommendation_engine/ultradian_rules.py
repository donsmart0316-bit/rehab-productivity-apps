from __future__ import annotations


def focus_block_minutes(fatigue_score: float, burnout_risk: str, recovery_score: float, plan_type: str = "primary") -> int:
    base = 105
    if burnout_risk == "Medium":
        base -= 15
    if burnout_risk == "High":
        base -= 35
    if fatigue_score >= 7:
        base -= 20
    elif fatigue_score <= 3:
        base += 10
    if recovery_score < 45:
        base -= 15
    elif recovery_score > 75:
        base += 10
    if plan_type == "conservative":
        base -= 20
    elif plan_type == "high_performance" and burnout_risk != "High":
        base += 15
    return int(max(45, min(120, round(base / 5) * 5)))


def break_minutes(fatigue_score: float, burnout_risk: str, recovery_score: float, plan_type: str = "primary") -> int:
    base = 12
    if burnout_risk == "Medium":
        base += 5
    if burnout_risk == "High":
        base += 12
    if fatigue_score >= 7:
        base += 8
    if recovery_score < 45:
        base += 8
    if plan_type == "conservative":
        base += 8
    elif plan_type == "high_performance" and burnout_risk == "Low":
        base -= 3
    return int(max(8, min(30, round(base / 5) * 5)))


def ultradian_recommendation(fatigue_score: float, burnout_risk: str, recovery_score: float, plan_type: str = "primary") -> dict[str, int | str]:
    focus = focus_block_minutes(fatigue_score, burnout_risk, recovery_score, plan_type)
    rest = break_minutes(fatigue_score, burnout_risk, recovery_score, plan_type)
    return {
        "focus_block_minutes": focus,
        "break_minutes": rest,
        "pattern": f"{focus} min focus + {rest} min recovery",
    }

