from __future__ import annotations


def recovery_status(recovery_score: float) -> str:
    if recovery_score >= 85:
        return "Excellent"
    if recovery_score >= 70:
        return "Good"
    if recovery_score >= 50:
        return "Moderate"
    if recovery_score >= 30:
        return "Fatigued"
    return "High Recovery Need"


def recovery_interventions(work_hours: float, fatigue_score: float, recovery_score: float, burnout_risk: str, screen_time_hours: float | None = None) -> list[dict[str, str | int]]:
    screen_hours = screen_time_hours if screen_time_hours is not None else max(work_hours, 4)
    status = recovery_status(recovery_score)
    posture_interval = 45 if fatigue_score >= 6 or work_hours >= 8 else 60
    mobility_frequency = "every 90 minutes"
    if status in {"Fatigued", "High Recovery Need"} or burnout_risk == "High":
        mobility_frequency = "every 60 minutes"
    interventions = [
        {
            "type": "Posture Reset",
            "frequency_minutes": posture_interval,
            "details": "Stand tall, reset shoulder blades, gently tuck chin, breathe slowly for 5 cycles.",
        },
        {
            "type": "20-20-20 Eye Strain Rule",
            "frequency_minutes": 20,
            "details": "Every 20 minutes, look 20 feet away for 20 seconds.",
        },
        {
            "type": "Mobility Break",
            "frequency": mobility_frequency,
            "details": "Alternate neck mobility, thoracic extension, lumbar mobility, and a short walk.",
        },
    ]
    if screen_hours >= 7:
        interventions.append(
            {
                "type": "Screen Load Reduction",
                "frequency": "midday and late afternoon",
                "details": "Batch screen-heavy tasks, dim glare, and use an off-screen planning break.",
            }
        )
    if recovery_score < 50:
        interventions.append(
            {
                "type": "Recovery Priority",
                "frequency": "today",
                "details": "Protect a longer walk or low-intensity mobility session before adding extra work.",
            }
        )
    return interventions

