from __future__ import annotations

import bootstrap

bootstrap.page_config("Home")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.cards import metric_card, risk_card
from app.components.forms import sidebar_profile
from app.components.metrics import recovery_label
from app.services.history_service import load_daily_history


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")
history = load_daily_history(user_id)

bootstrap.hero(
    "Design your day around",
    "your nervous system.",
    "A physiologically informed planning system for focus, recovery, burnout prevention, and sustainable performance.",
    pills=["Circadian planning", "Burnout risk", "Recovery intelligence", "Feedback loops"],
)

if history.empty:
    st.info("Start with the Daily Planner page to generate your first personalized plan.")
else:
    latest = history.iloc[-1]
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Latest Productivity", f"{latest['productivity_score']:.0f}/100", "Predicted daily output")
    with col2:
        risk_card(str(latest["burnout_risk"]))
    with col3:
        metric_card("Recovery", f"{latest['recovery_score']:.0f}/100", recovery_label(float(latest["recovery_score"])), "#2bbf7f")

bootstrap.section(
    "Workflow",
    "From check-in to better decisions",
    "The app turns sleep, stress, workload, tasks, and feedback into an adaptive schedule and coaching loop.",
)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("#### 1. Check in")
    st.write("Enter sleep, stress, workload, energy, and tasks.")
with col2:
    st.markdown("#### 2. Get the plan")
    st.write("Receive productivity, burnout, recovery, and a scheduled day.")
with col3:
    st.markdown("#### 3. Learn and improve")
    st.write("Review trends, export plans, and record feedback.")

st.page_link("pages/Daily_Planner.py", label="Open Daily Planner", icon=":material/event_available:")
