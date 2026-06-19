from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def page_config(title: str, icon: str = "PR") -> None:
    import streamlit as st

    st.set_page_config(
        page_title=f"{title} | Productivity & Recovery Coach",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_global_styles() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        :root {
            --coach-green: #4f8f6d;
            --coach-blue: #517ea6;
            --coach-amber: #c7923e;
            --coach-rose: #b96a6a;
            --panel-border: rgba(127, 127, 127, 0.22);
        }
        .coach-card {
            border: 1px solid var(--panel-border);
            border-radius: 8px;
            padding: 1rem;
            background: rgba(127, 127, 127, 0.06);
            min-height: 112px;
        }
        .coach-card h3 {
            margin: 0 0 .35rem 0;
            font-size: .95rem;
            font-weight: 650;
        }
        .coach-card .value {
            font-size: 2rem;
            font-weight: 760;
            line-height: 1.1;
        }
        .coach-card .caption {
            margin-top: .35rem;
            opacity: .78;
            font-size: .88rem;
        }
        .timeline-item {
            border-left: 4px solid var(--coach-blue);
            border-radius: 6px;
            padding: .65rem .85rem;
            margin-bottom: .55rem;
            background: rgba(127, 127, 127, 0.06);
        }
        .timeline-item.break {
            border-left-color: var(--coach-green);
        }
        .timeline-time {
            font-size: .82rem;
            opacity: .72;
            margin-bottom: .18rem;
        }
        .timeline-title {
            font-weight: 700;
        }
        .small-muted {
            opacity: .74;
            font-size: .9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
