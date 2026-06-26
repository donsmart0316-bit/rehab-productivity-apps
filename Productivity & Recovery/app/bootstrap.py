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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        :root {
            --coach-ink: #151515;
            --coach-muted: #61646f;
            --coach-soft: #f7f9ff;
            --coach-blue: #3157ff;
            --coach-lime: #b8ff63;
            --coach-coral: #ff6b5f;
            --coach-cyan: #00c2ff;
            --coach-amber: #ffb020;
            --coach-rose: #ff4d6d;
            --coach-paper: #ffffff;
            --panel-border: rgba(21, 21, 21, 0.13);
            --coach-shadow: 0 18px 44px rgba(21, 21, 21, 0.10);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                linear-gradient(rgba(49, 87, 255, 0.055) 1px, transparent 1px),
                linear-gradient(90deg, rgba(49, 87, 255, 0.055) 1px, transparent 1px),
                linear-gradient(135deg, #fbfcff 0%, #f7f9ff 48%, #f3fff6 100%);
            background-size: 38px 38px, 38px 38px, auto;
            color: var(--coach-ink);
        }

        .block-container {
            max-width: 1240px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3 {
            color: var(--coach-ink);
            letter-spacing: -0.03em;
        }

        div[data-testid="stMarkdownContainer"] p {
            color: var(--coach-muted);
        }

        section.coach-hero {
            position: relative;
            overflow: hidden;
            min-height: 310px;
            padding: 46px 52px;
            margin: 0 0 28px;
            border-radius: 18px;
            border: 2px solid rgba(21, 21, 21, 0.92);
            background:
                linear-gradient(90deg, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.96) 58%, rgba(21,21,21,0.98) 58%, rgba(21,21,21,0.98) 100%);
            box-shadow: 10px 10px 0 rgba(21, 21, 21, 0.92);
        }

        section.coach-hero:before {
            content: "";
            position: absolute;
            width: 355px;
            height: 86px;
            right: 74px;
            top: 70px;
            border-radius: 999px;
            background: var(--coach-lime);
            border: 2px solid #151515;
            transform: rotate(-8deg);
            box-shadow: 8px 8px 0 rgba(0,194,255,0.85);
        }

        section.coach-hero:after {
            content: "";
            position: absolute;
            right: 132px;
            bottom: 58px;
            width: 245px;
            height: 160px;
            border-radius: 18px;
            transform: rotate(4deg);
            background:
                repeating-linear-gradient(0deg, rgba(255,255,255,0.24) 0 2px, transparent 2px 20px),
                linear-gradient(135deg, var(--coach-blue), var(--coach-cyan));
            border: 2px solid #151515;
            box-shadow: 9px 9px 0 var(--coach-coral);
        }

        .coach-hero-content {
            position: relative;
            z-index: 2;
            max-width: 720px;
        }

        .coach-eyebrow {
            display: inline-flex;
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--coach-lime);
            color: #151515;
            border: 2px solid #151515;
            font-size: 0.76rem;
            font-weight: 900;
            letter-spacing: 0.13em;
            text-transform: uppercase;
            margin-bottom: 18px;
        }

        .coach-hero-title {
            margin: 0;
            max-width: 760px;
            color: var(--coach-ink);
            font-size: clamp(2.35rem, 5.2vw, 5rem);
            line-height: 0.92;
            font-weight: 900;
            letter-spacing: -0.06em;
        }

        .coach-hero-title span {
            background: linear-gradient(100deg, var(--coach-blue), var(--coach-coral), #151515);
            -webkit-background-clip: text;
            color: transparent;
        }

        .coach-hero-copy {
            margin-top: 22px;
            max-width: 660px;
            color: #465467;
            font-size: 1.12rem;
            line-height: 1.65;
            font-weight: 500;
        }

        .coach-pills {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 24px;
        }

        .coach-pill {
            padding: 9px 12px;
            border-radius: 12px;
            color: #101828;
            background: #ffffff;
            border: 2px solid #151515;
            box-shadow: 4px 4px 0 rgba(21, 21, 21, 0.86);
            font-size: 0.84rem;
            font-weight: 800;
        }

        .coach-section {
            margin: 24px 0 18px;
            padding: 24px 26px;
            border-radius: 18px;
            background: rgba(255,255,255,0.94);
            border: 2px solid rgba(21, 21, 21, 0.90);
            box-shadow: 7px 7px 0 rgba(21, 21, 21, 0.88);
        }

        .coach-section-label {
            display: inline-flex;
            padding: 7px 11px;
            border-radius: 999px;
            background: #151515;
            color: var(--coach-lime);
            font-size: 0.74rem;
            font-weight: 900;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .coach-section-title {
            margin: 0 0 8px;
            color: var(--coach-ink);
            font-size: 1.55rem;
            line-height: 1.15;
            font-weight: 900;
            letter-spacing: -0.03em;
        }

        .coach-section-copy {
            margin: 0;
            max-width: 780px;
            color: var(--coach-muted);
            line-height: 1.55;
            font-weight: 500;
        }

        .coach-card {
            border: 2px solid rgba(21, 21, 21, 0.90);
            border-radius: 18px;
            padding: 1.15rem 1.25rem;
            background: var(--coach-paper);
            min-height: 130px;
            box-shadow: 6px 6px 0 rgba(21, 21, 21, 0.88);
        }

        .coach-card:before {
            content: "";
            display: block;
            width: 56px;
            height: 6px;
            border-radius: 0;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, var(--coach-blue), var(--coach-lime), var(--coach-coral));
        }

        .coach-card h3 {
            margin: 0 0 .4rem 0;
            color: #667085;
            font-size: .92rem;
            font-weight: 800;
        }

        .coach-card .value {
            font-size: 2.18rem;
            font-weight: 900;
            line-height: 1.1;
            letter-spacing: -0.04em;
        }

        .coach-card .caption {
            margin-top: .5rem;
            color: #667085;
            font-size: .88rem;
            font-weight: 500;
        }

        .timeline-item {
            border-left: 10px solid var(--coach-blue);
            border-radius: 16px;
            padding: .85rem 1rem;
            margin-bottom: .75rem;
            background: #ffffff;
            border-top: 2px solid rgba(21, 21, 21, 0.90);
            border-right: 2px solid rgba(21, 21, 21, 0.90);
            border-bottom: 2px solid rgba(21, 21, 21, 0.90);
            box-shadow: 5px 5px 0 rgba(21, 21, 21, 0.86);
        }

        .timeline-item.break {
            border-left-color: var(--coach-lime);
            background: #fbfff4;
        }

        .timeline-time {
            font-size: .82rem;
            color: #667085;
            margin-bottom: .18rem;
            font-weight: 800;
        }

        .timeline-title {
            color: var(--coach-ink);
            font-weight: 850;
            letter-spacing: -0.01em;
        }

        .small-muted {
            color: #667085;
            font-size: .9rem;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-baseweb="select"] > div,
        div[data-testid="stFileUploader"] section {
            border-radius: 16px !important;
            border-color: var(--panel-border) !important;
            background: #ffffff !important;
            box-shadow: 3px 3px 0 rgba(21, 21, 21, 0.10);
        }

        label, div[data-testid="stWidgetLabel"] p {
            color: #233044 !important;
            font-weight: 800 !important;
        }

        .stButton>button,
        .stDownloadButton>button,
        div[data-testid="stFormSubmitButton"] button {
            min-height: 50px;
            border: 2px solid #151515;
            border-radius: 14px;
            background: var(--coach-lime);
            color: #151515;
            font-weight: 900;
            letter-spacing: -0.01em;
            box-shadow: 6px 6px 0 #151515;
            transition: transform 160ms ease, box-shadow 160ms ease;
        }

        .stButton>button:hover,
        .stDownloadButton>button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            color: #151515;
            transform: translateY(-2px);
            box-shadow: 8px 8px 0 #151515;
        }

        div[data-testid="stExpander"] {
            border-radius: 22px;
            border: 2px solid rgba(21, 21, 21, 0.14);
            background: rgba(255,255,255,0.92);
            box-shadow: 0 12px 24px rgba(17, 24, 39, 0.06);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 22px;
            overflow: hidden;
            border: 2px solid rgba(21, 21, 21, 0.16);
            box-shadow: 0 14px 28px rgba(17, 24, 39, 0.06);
        }

        .stAlert {
            border-radius: 18px;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px),
                #151515;
            background-size: 28px 28px;
        }

        [data-testid="stSidebar"] * {
            color: rgba(255,255,255,0.92);
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            color: #101828 !important;
            background: rgba(255,255,255,0.96) !important;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            section.coach-hero {
                padding: 34px 24px;
                border-radius: 26px;
                min-height: 0;
            }

            section.coach-hero:after {
                opacity: 0.18;
                right: -92px;
                bottom: 30px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, accent: str, body: str, eyebrow: str = "Productivity & Recovery", pills: list[str] | None = None) -> None:
    import html
    import streamlit as st

    pill_html = "".join(f'<span class="coach-pill">{html.escape(item)}</span>' for item in (pills or []))
    st.markdown(
        f"""
        <section class="coach-hero">
            <div class="coach-hero-content">
                <div class="coach-eyebrow">{html.escape(eyebrow)}</div>
                <h1 class="coach-hero-title">{html.escape(title)} <span>{html.escape(accent)}</span></h1>
                <p class="coach-hero-copy">{html.escape(body)}</p>
                <div class="coach-pills">{pill_html}</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section(label: str, title: str, body: str) -> None:
    import html
    import streamlit as st

    st.markdown(
        f"""
        <div class="coach-section">
            <div class="coach-section-label">{html.escape(label)}</div>
            <h2 class="coach-section-title">{html.escape(title)}</h2>
            <p class="coach-section-copy">{html.escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
