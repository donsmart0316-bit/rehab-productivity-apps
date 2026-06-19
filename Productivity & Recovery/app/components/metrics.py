from __future__ import annotations


def recovery_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Moderate"
    if score >= 30:
        return "Fatigued"
    return "High Recovery Need"
