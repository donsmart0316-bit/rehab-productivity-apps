from __future__ import annotations

import html

import streamlit as st


RISK_COLORS = {"Low": "#4f8f6d", "Medium": "#c7923e", "High": "#b96a6a"}


def metric_card(title: str, value: str | float | int, caption: str = "", color: str = "#517ea6") -> None:
    st.markdown(
        f"""
        <div class="coach-card">
          <h3>{html.escape(title)}</h3>
          <div class="value" style="color:{color};">{html.escape(str(value))}</div>
          <div class="caption">{html.escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_card(risk: str) -> None:
    metric_card("Burnout Risk", risk, "Current risk category", RISK_COLORS.get(risk, "#c7923e"))


def timeline(schedule: list[dict]) -> None:
    for item in schedule:
        css_class = "timeline-item break" if item.get("item_type") == "break" else "timeline-item"
        st.markdown(
            f"""
            <div class="{css_class}">
              <div class="timeline-time">{html.escape(item.get("start", ""))} - {html.escape(item.get("end", ""))}</div>
              <div class="timeline-title">{html.escape(item.get("title", ""))}</div>
              <div class="small-muted">Category: {html.escape(item.get("task_category") or item.get("item_type", ""))}</div>
              <div class="small-muted">{html.escape(item.get("reason", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
