from __future__ import annotations

from datetime import date
from io import StringIO

import pandas as pd
import streamlit as st


def sidebar_profile() -> dict:
    st.sidebar.header("User Profile")
    stored_name = "" if st.session_state.get("profile_name") == "Demo User" else st.session_state.get("profile_name", "")
    stored_occupation = "" if st.session_state.get("profile_occupation") == "Knowledge Worker" else st.session_state.get("profile_occupation", "")
    raw_name = st.sidebar.text_input("Name", value=stored_name, placeholder="e.g., Alex")
    raw_occupation = st.sidebar.text_input("Occupation", value=stored_occupation, placeholder="e.g., Product Manager")
    profile = {
        "name": raw_name.strip() or "Guest User",
        "age": st.sidebar.number_input("Age", min_value=13, max_value=90, value=int(st.session_state.get("profile_age", 32))),
        "occupation": raw_occupation.strip() or "Knowledge Worker",
        "chronotype": st.sidebar.selectbox("Chronotype", ["Morning", "Intermediate", "Evening"], index=["Morning", "Intermediate", "Evening"].index(st.session_state.get("chronotype", "Intermediate"))),
        "start_hour": st.sidebar.slider("Workday Start", 5, 12, int(st.session_state.get("start_hour", 8))),
        "end_hour": st.sidebar.slider("Workday End", 13, 22, int(st.session_state.get("end_hour", 18))),
        "work_style": st.sidebar.selectbox("Work Style", ["Deep Work", "Meeting Heavy", "Balanced", "Flexible"], index=2),
        "productivity_goal": st.sidebar.selectbox("Productivity Goal", ["Balanced", "Maximum Productivity", "Recovery First"], index=0),
        "exercise_preference": st.sidebar.selectbox("Exercise Preference", ["Walking", "Mobility", "Strength", "Gentle Stretching"], index=0),
        "break_style": st.sidebar.selectbox("Preferred Break Style", ["Movement", "Breathing", "Outdoor Walk", "Quiet Reset"], index=0),
        "sleep_need": st.sidebar.slider("Sleep Need", 7.0, 9.5, float(st.session_state.get("sleep_need", 8.0)), 0.25),
    }
    st.session_state["profile_name"] = raw_name
    st.session_state["profile_occupation"] = raw_occupation
    for key, value in profile.items():
        if key not in {"name", "occupation"}:
            st.session_state[f"profile_{key}"] = value
    st.session_state["chronotype"] = profile["chronotype"]
    st.session_state["start_hour"] = profile["start_hour"]
    st.session_state["end_hour"] = profile["end_hour"]
    st.session_state["sleep_need"] = profile["sleep_need"]
    return profile


def parse_tasks(uploaded_file, manual_text: str) -> list[dict]:
    if uploaded_file is not None:
        frame = pd.read_csv(uploaded_file)
    else:
        text = manual_text.strip()
        if not text:
            return []
        frame = pd.read_csv(StringIO(text), header=None, names=["Task", "Minutes", "Complexity", "Priority"])
    tasks = []
    for _, row in frame.iterrows():
        name = str(row.get("Task") or row.get("task") or row.iloc[0]).strip()
        if not name:
            continue
        complexity = row.get("Complexity", row.get("complexity", 5))
        if isinstance(complexity, str):
            complexity = {"low": 2, "medium": 5, "high": 8}.get(complexity.strip().lower(), 5)
        complexity_value = pd.to_numeric(complexity, errors="coerce")
        if pd.isna(complexity_value):
            complexity_value = 5
        minutes_value = pd.to_numeric(row.get("Minutes", row.get("minutes", 60)), errors="coerce")
        priority_value = pd.to_numeric(row.get("Priority", row.get("priority", 3)), errors="coerce")
        minutes = int(60 if pd.isna(minutes_value) else minutes_value)
        priority = int(3 if pd.isna(priority_value) else priority_value)
        tasks.append({"name": name, "estimated_minutes": max(10, minutes), "complexity": int(max(1, min(10, complexity_value))), "priority": int(max(1, min(5, priority)))})
    return tasks


def daily_checkin_form(profile: dict) -> tuple[dict | None, list[dict] | None]:
    with st.form("daily_checkin"):
        st.subheader("Daily Check-In")
        col1, col2, col3 = st.columns(3)
        with col1:
            checkin_date = st.date_input("Date", value=date.today())
            sleep_hours = st.slider("Sleep Hours", 3.0, 10.5, 7.2, 0.25)
            sleep_quality = st.slider("Sleep Quality", 0.0, 10.0, 6.5, 0.5)
            energy_level = st.slider("Energy Level", 0.0, 10.0, 6.0, 0.5)
        with col2:
            mood_score = st.slider("Mood Score", 0.0, 10.0, 6.0, 0.5)
            stress_level = st.slider("Stress Level", 0.0, 10.0, 5.0, 0.5)
            fatigue_score = st.slider("Fatigue Score", 0.0, 10.0, 4.5, 0.5)
            activity_minutes = st.number_input("Activity Minutes", min_value=0, max_value=240, value=35)
        with col3:
            work_hours = st.slider("Work Hours", 0.0, 14.0, 8.0, 0.25)
            meeting_hours = st.slider("Meeting Hours", 0.0, 8.0, 1.5, 0.25)
            task_count = st.number_input("Task Count", min_value=0, max_value=30, value=4)
            task_complexity = st.slider("Average Task Complexity", 0.0, 10.0, 5.5, 0.5)

        st.markdown("#### Tasks")
        uploaded = st.file_uploader("Upload tasks CSV", type=["csv"], help="Columns: Task, Minutes, Complexity, Priority")
        manual = st.text_area(
            "Or enter tasks as CSV rows",
            value="",
            placeholder="Research Report,100,9,5\nClient Meeting,45,4,4\nEmail Cleanup,35,2,2",
            height=120,
        )
        submitted = st.form_submit_button("Generate Today's Plan", type="primary")
    if not submitted:
        return None, None
    checkin = {
        "date": checkin_date.isoformat(),
        "sleep_hours": sleep_hours,
        "sleep_quality": sleep_quality,
        "energy_level": energy_level,
        "mood_score": mood_score,
        "stress_level": stress_level,
        "fatigue_score": fatigue_score,
        "activity_minutes": activity_minutes,
        "work_hours": work_hours,
        "meeting_hours": meeting_hours,
        "task_count": int(task_count),
        "task_complexity": task_complexity,
        "chronotype": profile["chronotype"],
        "sleep_need": profile["sleep_need"],
    }
    return checkin, parse_tasks(uploaded, manual)
