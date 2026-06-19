from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("History")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.forms import sidebar_profile
from app.services.history_service import load_daily_history, load_plan_history


profile = sidebar_profile()
user_id = profile["name"].lower().replace(" ", "_")
history = load_daily_history(user_id)

st.title("History")
if history.empty:
    st.info("Your previous predictions and plans will appear here.")
else:
    st.dataframe(history.sort_values("date", ascending=False), use_container_width=True)

st.subheader("Saved Plans")
records = [record for record in load_plan_history() if record.get("profile", {}).get("name", "").lower().replace(" ", "_") == user_id]
for record in reversed(records[-10:]):
    with st.expander(f"{record['checkin']['date']} - Productivity {record['prediction']['productivity_score']}/100 - {record['prediction']['burnout_risk']} risk"):
        for item in record["plan"].get("schedule", []):
            st.write(f"**{item['start']}-{item['end']}** {item['title']}: {item.get('reason', '')}")
