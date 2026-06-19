from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def circadian_line(profile: list[dict], column: str, title: str, y_label: str) -> go.Figure:
    frame = pd.DataFrame(profile)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["hour"],
            y=frame[column],
            mode="lines+markers",
            line=dict(width=3, color="#517ea6"),
            marker=dict(size=6),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Hour",
        yaxis_title=y_label,
        height=340,
        margin=dict(l=24, r=24, t=55, b=32),
    )
    return fig


def burnout_gauge(risk: str) -> go.Figure:
    value = {"Low": 20, "Medium": 55, "High": 85}.get(risk, 55)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": " risk"},
            title={"text": f"Burnout: {risk}"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#517ea6"},
                "steps": [
                    {"range": [0, 33], "color": "rgba(79,143,109,.35)"},
                    {"range": [33, 66], "color": "rgba(199,146,62,.35)"},
                    {"range": [66, 100], "color": "rgba(185,106,106,.35)"},
                ],
            },
        )
    )
    fig.update_layout(height=290, margin=dict(l=18, r=18, t=45, b=18))
    return fig


def trend_line(frame: pd.DataFrame, column: str, title: str, y_label: str) -> go.Figure:
    fig = go.Figure()
    if not frame.empty and column in frame.columns:
        fig.add_trace(go.Scatter(x=frame["date"], y=frame[column], mode="lines+markers", line=dict(width=3)))
    fig.update_layout(title=title, xaxis_title="Date", yaxis_title=y_label, height=330, margin=dict(l=24, r=24, t=55, b=32))
    return fig
