from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("Weekly Overview")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.cards import metric_card, risk_card
from app.components.forms import sidebar_profile
from app.components.metrics import recovery_label
from app.services.history_service import load_daily_history
from app.services.llm_service import weekly_coaching


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")
history = load_daily_history(user_id).tail(7)

st.title("Weekly Overview")
if history.empty:
    st.info("Generate at least one daily plan before viewing weekly insights.")
    st.stop()

avg_productivity = history["productivity_score"].mean()
avg_recovery = history["recovery_score"].mean()
latest_risk = str(history.iloc[-1]["burnout_risk"])

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Average Productivity", f"{avg_productivity:.0f}/100", "Last 7 records")
with col2:
    risk_card(latest_risk)
with col3:
    metric_card("Average Recovery", f"{avg_recovery:.0f}/100", recovery_label(avg_recovery), "#4f8f6d")

best_day = history.loc[history["productivity_score"].idxmax()]
low_recovery = history.loc[history["recovery_score"].idxmin()]
st.subheader("Weekly Insights")
st.write(f"Most productive day: **{best_day['date'].date()}** with productivity **{best_day['productivity_score']:.0f}/100**.")
st.write(f"Lowest recovery day: **{low_recovery['date'].date()}** with recovery **{low_recovery['recovery_score']:.0f}/100**.")

st.subheader("Weekly Recommendations")
if avg_recovery < 55:
    st.write("- Reduce cognitive load for one day this week and protect a longer recovery block.")
if history["sleep_debt"].mean() > 4:
    st.write("- Prioritize sleep consistency before adding more focus blocks.")
if (history["burnout_risk"] == "High").any():
    st.write("- Use the conservative plan on high-risk days and avoid stacking meetings after deep work.")
if avg_recovery >= 70 and latest_risk == "Low":
    st.write("- Keep demanding work in your chronotype peak window and maintain preventive breaks.")

context = {"profile": profile, "weekly_average_productivity": avg_productivity, "weekly_average_recovery": avg_recovery, "latest_burnout_risk": latest_risk}
with st.expander("AI Weekly Coaching Summary"):
    st.markdown(weekly_coaching(context, {}))
