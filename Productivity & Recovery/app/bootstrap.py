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
            --coach-ink: #101828;
            --coach-muted: #667085;
            --coach-soft: #f8fafc;
            --coach-blue: #335cff;
            --coach-violet: #7c3aed;
            --coach-green: #00b894;
            --coach-cyan: #38bdf8;
            --coach-amber: #f59e0b;
            --coach-rose: #ef4444;
            --coach-lavender: #f4f0ff;
            --panel-border: rgba(216, 222, 233, 0.95);
            --coach-shadow: 0 24px 70px rgba(17, 24, 39, 0.12);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 86% 2%, rgba(124, 58, 237, 0.18), transparent 34%),
                radial-gradient(circle at 8% 24%, rgba(0, 184, 148, 0.13), transparent 30%),
                linear-gradient(135deg, #f8fafc 0%, #f4f0ff 50%, #ecfdf5 100%);
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
            padding: 48px 54px;
            margin: 0 0 28px;
            border-radius: 34px;
            border: 1px solid var(--panel-border);
            background:
                linear-gradient(118deg, rgba(255,255,255,0.96) 0%, rgba(244,240,255,0.94) 50%, rgba(236,253,245,0.92) 100%);
            box-shadow: var(--coach-shadow);
        }

        section.coach-hero:before {
            content: "";
            position: absolute;
            width: 440px;
            height: 440px;
            right: -120px;
            top: -130px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(124,58,237,0.34), rgba(51,92,255,0.16) 48%, transparent 70%);
        }

        section.coach-hero:after {
            content: "";
            position: absolute;
            right: 76px;
            bottom: 44px;
            width: 310px;
            height: 205px;
            border-radius: 42px;
            transform: rotate(-6deg);
            background:
                linear-gradient(135deg, rgba(51,92,255,0.96), rgba(124,58,237,0.88) 54%, rgba(0,184,148,0.88));
            box-shadow: 0 34px 82px rgba(51, 92, 255, 0.26);
        }

        .coach-hero-content {
            position: relative;
            z-index: 2;
            max-width: 720px;
        }

        .coach-eyebrow {
            display: inline-flex;
            padding: 8px 13px;
            border-radius: 999px;
            background: rgba(51, 92, 255, 0.10);
            color: var(--coach-blue);
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
            font-size: clamp(2.45rem, 5.4vw, 5.2rem);
            line-height: 0.96;
            font-weight: 900;
            letter-spacing: -0.055em;
        }

        .coach-hero-title span {
            background: linear-gradient(105deg, var(--coach-blue), var(--coach-violet), var(--coach-green));
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
            padding: 9px 13px;
            border-radius: 999px;
            color: #101828;
            background: rgba(255,255,255,0.78);
            border: 1px solid var(--panel-border);
            font-size: 0.84rem;
            font-weight: 800;
        }

        .coach-section {
            margin: 24px 0 18px;
            padding: 24px 26px;
            border-radius: 28px;
            background: rgba(255,255,255,0.72);
            border: 1px solid var(--panel-border);
            box-shadow: 0 20px 52px rgba(17, 24, 39, 0.08);
        }

        .coach-section-label {
            display: inline-flex;
            padding: 7px 11px;
            border-radius: 999px;
            background: #eef2ff;
            color: var(--coach-blue);
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
            border: 1px solid var(--panel-border);
            border-radius: 24px;
            padding: 1.15rem 1.25rem;
            background: rgba(255, 255, 255, 0.92);
            min-height: 130px;
            box-shadow: 0 18px 42px rgba(17, 24, 39, 0.08);
        }

        .coach-card:before {
            content: "";
            display: block;
            width: 56px;
            height: 6px;
            border-radius: 999px;
            margin-bottom: 1rem;
            background: linear-gradient(105deg, var(--coach-blue), var(--coach-green));
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
            border-left: 6px solid var(--coach-blue);
            border-radius: 18px;
            padding: .85rem 1rem;
            margin-bottom: .75rem;
            background: rgba(255, 255, 255, 0.92);
            border-top: 1px solid var(--panel-border);
            border-right: 1px solid var(--panel-border);
            border-bottom: 1px solid var(--panel-border);
            box-shadow: 0 14px 32px rgba(17, 24, 39, 0.06);
        }

        .timeline-item.break {
            border-left-color: var(--coach-green);
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
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 10px 26px rgba(17, 24, 39, 0.04);
        }

        label, div[data-testid="stWidgetLabel"] p {
            color: #233044 !important;
            font-weight: 800 !important;
        }

        .stButton>button,
        .stDownloadButton>button,
        div[data-testid="stFormSubmitButton"] button {
            min-height: 50px;
            border: none;
            border-radius: 16px;
            background: linear-gradient(105deg, var(--coach-blue), var(--coach-violet), var(--coach-green));
            color: white;
            font-weight: 900;
            letter-spacing: -0.01em;
            box-shadow: 0 18px 34px rgba(51, 92, 255, 0.22);
            transition: transform 160ms ease, box-shadow 160ms ease;
        }

        .stButton>button:hover,
        .stDownloadButton>button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 24px 42px rgba(51, 92, 255, 0.30);
        }

        div[data-testid="stExpander"] {
            border-radius: 22px;
            border: 1px solid var(--panel-border);
            background: rgba(255,255,255,0.76);
            box-shadow: 0 16px 36px rgba(17, 24, 39, 0.06);
        }

        div[data-testid="stDataFrame"] {
            border-radius: 22px;
            overflow: hidden;
            border: 1px solid var(--panel-border);
            box-shadow: 0 18px 42px rgba(17, 24, 39, 0.06);
        }

        .stAlert {
            border-radius: 18px;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1020 0%, #13213e 100%);
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
