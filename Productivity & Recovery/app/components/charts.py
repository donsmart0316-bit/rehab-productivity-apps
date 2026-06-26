from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def circadian_line(profile: list[dict], column: str, title: str, y_label: str) -> go.Figure:
    frame = pd.DataFrame(profile)
    fig = go.Figure()
    color = "#00c2ff" if "energy" in column else "#3157ff"
    fig.add_trace(
        go.Scatter(
            x=frame["hour"],
            y=frame[column],
            mode="lines+markers",
            line=dict(width=4, color=color),
            marker=dict(size=8, color="#b8ff63", line=dict(width=2, color="#151515")),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Hour",
        yaxis_title=y_label,
        height=340,
        margin=dict(l=24, r=24, t=55, b=32),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#151515"),
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
                "bar": {"color": "#3157ff"},
                "steps": [
                    {"range": [0, 33], "color": "rgba(184,255,99,.58)"},
                    {"range": [33, 66], "color": "rgba(255,176,32,.46)"},
                    {"range": [66, 100], "color": "rgba(255,77,109,.40)"},
                ],
            },
        )
    )
    fig.update_layout(height=290, margin=dict(l=18, r=18, t=45, b=18), paper_bgcolor="rgba(255,255,255,0)", font=dict(color="#151515"))
    return fig


def trend_line(frame: pd.DataFrame, column: str, title: str, y_label: str) -> go.Figure:
    fig = go.Figure()
    if not frame.empty and column in frame.columns:
        fig.add_trace(
            go.Scatter(
                x=frame["date"],
                y=frame[column],
                mode="lines+markers",
                line=dict(width=4, color="#3157ff"),
                marker=dict(size=8, color="#b8ff63", line=dict(width=2, color="#151515")),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        height=330,
        margin=dict(l=24, r=24, t=55, b=32),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#ffffff",
        font=dict(color="#151515"),
    )
    return fig
