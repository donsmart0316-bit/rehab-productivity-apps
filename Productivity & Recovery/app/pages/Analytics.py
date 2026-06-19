from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("Analytics")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.charts import burnout_gauge, trend_line
from app.components.forms import sidebar_profile
from app.services.analytics_service import adherence_score, aggregate_insights, habit_consistency, period_summary
from app.services.history_service import load_daily_history


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")
history = load_daily_history(user_id)

st.title("Analytics")
if history.empty:
    st.info("No history yet. Generate daily plans to unlock trend analytics.")
    st.stop()

consistency = habit_consistency(history)
adherence = adherence_score(user_id)
col0, col00, col000 = st.columns(3)
with col0:
    st.metric("Sleep Consistency", f"{consistency['sleep_consistency']:.0f}/100")
with col00:
    st.metric("Activity Consistency", f"{consistency['activity_consistency']:.0f}/100")
with col000:
    st.metric("Adherence", "N/A" if adherence is None else f"{adherence:.0f}%")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(trend_line(history, "productivity_score", "Productivity Trend", "Productivity"), use_container_width=True)
with col2:
    st.plotly_chart(trend_line(history, "recovery_score", "Recovery Trend", "Recovery"), use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(trend_line(history, "sleep_debt", "Sleep Debt Trend", "Hours"), use_container_width=True)
with col4:
    st.plotly_chart(burnout_gauge(str(history.iloc[-1]["burnout_risk"])), use_container_width=True)

st.subheader("Recent Data")
st.dataframe(history.tail(14), use_container_width=True)

st.subheader("Period Summaries")
summary_tabs = st.tabs(["Weekly", "Monthly", "Quarterly"])
for tab, period in zip(summary_tabs, ["W", "M", "Q"]):
    with tab:
        st.dataframe(period_summary(history, period), use_container_width=True)

st.subheader("Personal Insights")
for insight in aggregate_insights(history):
    st.write(f"- {insight}")
