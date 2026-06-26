from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("Feedback")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.forms import sidebar_profile
from app.services.feedback_service import load_feedback, save_feedback


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")

bootstrap.hero(
    "Close the loop with",
    "real feedback.",
    "Tell the coach what worked, what felt heavy, and how the plan affected productivity, fatigue, and satisfaction.",
    eyebrow="Feedback",
    pills=["Adherence", "Fatigue", "Satisfaction", "Learning loop"],
)
latest_plan = st.session_state.get("latest_plan")
if latest_plan is None:
    st.info("Generate a daily plan first, then come back to record feedback.")
else:
    with st.form("feedback_form"):
        followed = st.radio("Did you follow the plan?", [True, False], format_func=lambda value: "Yes" if value else "No", horizontal=True)
        productivity = st.slider("Perceived Productivity", 1, 10, 7)
        fatigue = st.slider("Perceived Fatigue", 1, 10, 4)
        satisfaction = st.slider("Overall Satisfaction", 1, 10, 8)
        comments = st.text_area("Comments", height=100)
        submitted = st.form_submit_button("Save Feedback", type="primary")
    if submitted:
        save_feedback(user_id, latest_plan["date"], latest_plan, followed, productivity, fatigue, satisfaction, comments)
        st.success("Feedback saved.")

bootstrap.section("Feedback Log", "Recent learning signals", "Your feedback helps future planning become more personalized and realistic.")
feedback = load_feedback()
if feedback.empty:
    st.caption("No feedback recorded yet.")
else:
    st.dataframe(feedback.tail(20), use_container_width=True)
