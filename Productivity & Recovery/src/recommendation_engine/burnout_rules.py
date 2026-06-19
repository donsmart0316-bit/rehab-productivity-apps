from __future__ import annotations


def burnout_adjustments(burnout_risk: str, recovery_score: float, plan_type: str = "primary") -> dict[str, object]:
    risk = burnout_risk or "Medium"
    adjustments: dict[str, object] = {
        "risk": risk,
        "max_deep_work_blocks": 3,
        "reduce_workload": False,
        "avoid_over_scheduling": True,
        "notes": [],
    }
    if risk == "Medium":
        adjustments["max_deep_work_blocks"] = 2
        adjustments["notes"].append("Medium burnout risk: keep focus blocks shorter and add recovery between demanding tasks.")
    elif risk == "High":
        adjustments["max_deep_work_blocks"] = 1
        adjustments["reduce_workload"] = True
        adjustments["notes"].append("High burnout risk: lower workload, reduce cognitive demand, and prioritize recovery.")
    else:
        adjustments["notes"].append("Low burnout risk: normal workload is acceptable if breaks remain protected.")

    if recovery_score < 45:
        adjustments["max_deep_work_blocks"] = min(int(adjustments["max_deep_work_blocks"]), 1)
        adjustments["reduce_workload"] = True
        adjustments["notes"].append("Low recovery score: cap deep work and increase movement/recovery time.")

    if plan_type == "conservative":
        adjustments["max_deep_work_blocks"] = max(1, int(adjustments["max_deep_work_blocks"]) - 1)
        adjustments["reduce_workload"] = True
    elif plan_type == "high_performance" and risk == "Low" and recovery_score >= 70:
        adjustments["max_deep_work_blocks"] = 4

    return adjustments

