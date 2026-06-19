from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("Product Maturity")
bootstrap.inject_global_styles()

import pandas as pd
import streamlit as st

from app.components.cards import metric_card
from app.components.charts import trend_line
from app.components.forms import sidebar_profile
from app.services.analytics_service import adherence_score, aggregate_insights, habit_consistency, period_summary
from app.services.history_service import load_daily_history


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")
history = load_daily_history(user_id)

st.title("Product Maturity Dashboard")
st.caption("Longitudinal progress, confidence, adherence, and anonymized insights.")

if history.empty:
    st.info("Generate daily plans to populate maturity analytics.")
    st.stop()

consistency = habit_consistency(history)
adherence = adherence_score(user_id)
latest = history.iloc[-1]

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Sleep Consistency", f"{consistency['sleep_consistency']:.0f}/100", "Lower variation is better")
with col2:
    metric_card("Activity Consistency", f"{consistency['activity_consistency']:.0f}/100", "Stable movement habit")
with col3:
    metric_card("Adherence", "N/A" if adherence is None else f"{adherence:.0f}%", "From feedback records")
with col4:
    metric_card("Records", consistency["checkin_days"], "Daily check-ins")

st.subheader("Longitudinal Trends")
col_a, col_b = st.columns(2)
with col_a:
    st.plotly_chart(trend_line(history, "productivity_score", "Productivity Over Time", "Productivity"), use_container_width=True)
with col_b:
    st.plotly_chart(trend_line(history, "recovery_score", "Recovery Over Time", "Recovery"), use_container_width=True)

st.subheader("Summaries")
tabs = st.tabs(["Weekly", "Monthly", "Quarterly"])
for tab, period in zip(tabs, ["W", "M", "Q"]):
    with tab:
        summary = period_summary(history, period)
        st.dataframe(summary, use_container_width=True)

st.subheader("Anonymized Insights")
for insight in aggregate_insights(history):
    st.write(f"- {insight}")

if "productivity_confidence" in latest:
    st.subheader("Latest Confidence")
    st.write(
        f"Productivity confidence: **{latest.get('productivity_confidence', 'N/A')}** | "
        f"Burnout confidence: **{latest.get('burnout_confidence', 'N/A')}** | "
        f"Recommendation confidence: **{latest.get('recommendation_confidence', 'N/A')}**"
    )
