from __future__ import annotations

from app.bootstrap import PROJECT_ROOT
from src.feedback.feedback_store import FeedbackRecord, FeedbackStore
from src.monitoring.logger import log_feedback


def save_feedback(user_id: str, date: str, recommended_plan: dict, followed: bool, productivity: int, fatigue: int, satisfaction: int, comments: str) -> None:
    store = FeedbackStore(PROJECT_ROOT / "data" / "feedback" / "feedback_log.csv")
    store.append(
        FeedbackRecord(
            user_id=user_id,
            date=date,
            recommended_plan=recommended_plan,
            actual_plan_followed={"followed": followed},
            user_satisfaction_rating=satisfaction,
            perceived_productivity=productivity,
            perceived_fatigue=fatigue,
            comments=comments,
        )
    )
    log_feedback(
        PROJECT_ROOT,
        user_id,
        date,
        {
            "plan_followed": followed,
            "perceived_productivity": productivity,
            "perceived_fatigue": fatigue,
            "satisfaction": satisfaction,
            "comments": comments,
        },
    )


def load_feedback():
    return FeedbackStore(PROJECT_ROOT / "data" / "feedback" / "feedback_log.csv").load()
