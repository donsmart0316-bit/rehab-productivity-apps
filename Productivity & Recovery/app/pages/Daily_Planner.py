from __future__ import annotations

import app.bootstrap as bootstrap

bootstrap.page_config("Daily Planner")
bootstrap.inject_global_styles()

import streamlit as st

from app.components.cards import metric_card, risk_card, timeline
from app.components.charts import burnout_gauge, circadian_line
from app.components.forms import daily_checkin_form, sidebar_profile
from app.components.metrics import recovery_label
from app.services.export_service import plan_markdown, plan_pdf_bytes, plan_text
from app.services.history_service import append_daily_record
from app.services.llm_service import daily_coaching
from app.services.prediction_service import predict_daily
from app.services.recommendation_service import generate_plan


profile = sidebar_profile()
bootstrap.hero(
    "Plan today with",
    "recovery-aware intelligence.",
    "Generate a schedule from today's physiology, workload, task demands, chronotype, and burnout risk.",
    eyebrow="Daily Planner",
    pills=["Sleep debt", "Plan modes", "Focus blocks", "Recovery breaks"],
)

checkin, tasks = daily_checkin_form(profile)

if checkin and tasks is not None:
    if not tasks:
        st.warning("Add at least one task manually or upload a task CSV to generate a schedule.")
        st.stop()
    prediction, features = predict_daily(profile, checkin)
    plans = generate_plan(profile, checkin, prediction, tasks)
    selected_plan_name = st.radio("Plan Mode", ["primary", "conservative", "high_performance"], horizontal=True, format_func=lambda value: value.replace("_", " ").title())
    plan = plans[selected_plan_name]
    coaching = daily_coaching(profile, prediction, plan)
    append_daily_record(profile, checkin, prediction, features, plan, coaching)
    st.session_state["latest_profile"] = profile
    st.session_state["latest_checkin"] = checkin
    st.session_state["latest_prediction"] = prediction
    st.session_state["latest_plan"] = plan
    st.session_state["latest_coaching"] = coaching

if "latest_prediction" in st.session_state:
    prediction = st.session_state["latest_prediction"]
    plan = st.session_state["latest_plan"]
    coaching = st.session_state["latest_coaching"]
    profile = st.session_state.get("latest_profile", profile)

    bootstrap.section(
        "Prediction Dashboard",
        "Your performance readiness",
        "Live predictions combine the check-in, profile, model confidence, and recommendation guardrails.",
    )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Productivity", f"{prediction['productivity_score']:.0f}/100", "Expected usable output")
    with col2:
        risk_card(prediction["burnout_risk"])
    with col3:
        metric_card("Recovery", f"{prediction['recovery_score']:.0f}/100", recovery_label(prediction["recovery_score"]), "#00b894")
    with col4:
        metric_card("Sleep Debt", f"{prediction['sleep_debt']:.1f}h", "Estimated rolling deficit", "#c7923e")
    conf1, conf2, conf3 = st.columns(3)
    with conf1:
        metric_card("Productivity Confidence", prediction["productivity_confidence_label"], f"{prediction['productivity_confidence']:.0f}/100")
    with conf2:
        metric_card("Burnout Confidence", prediction["burnout_confidence_label"], f"{prediction['burnout_confidence']:.0f}/100")
    with conf3:
        metric_card("Schedule Confidence", prediction["recommendation_confidence_label"], f"{prediction['recommendation_confidence']:.0f}/100")
    if prediction.get("input_warnings"):
        with st.expander("Input quality notes"):
            for warning in prediction["input_warnings"]:
                st.write(f"- {warning}")
    validation = plan.get("rule_outputs", {}).get("validation", {})
    quality_score = plan.get("rule_outputs", {}).get("recommendation_quality_score")
    if quality_score is not None:
        st.caption(f"Recommendation Quality Score: {quality_score}/100")
    if validation and not validation.get("passed", True):
        st.error("This plan did not pass the recommendation quality gate. Review the validation notes before using it.")
        with st.expander("Validation notes"):
            for issue in validation.get("issues", []):
                st.write(f"- {issue}")
    deferred = plan.get("rule_outputs", {}).get("deferred_tasks", [])
    if deferred:
        with st.expander("Deferred tasks"):
            for item in deferred:
                st.write(f"- **{item['task']}**: {item['reason']}")

    tabs = st.tabs(["Schedule", "Coaching", "Insights", "Export"])
    with tabs[0]:
        timeline(plan["schedule"])
        with st.expander("Recovery Interventions"):
            for item in plan.get("recovery_interventions", []):
                st.write(f"**{item['type']}** - {item.get('details', '')}")
    with tabs[1]:
        st.markdown(coaching)
    with tabs[2]:
        profile_curve = plan["rule_outputs"]["circadian_profile"]
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(circadian_line(profile_curve, "hourly_energy", "Energy Curve", "Energy"), use_container_width=True)
        with col_b:
            st.plotly_chart(circadian_line(profile_curve, "hourly_productivity", "Productivity Curve", "Productivity"), use_container_width=True)
        st.plotly_chart(burnout_gauge(prediction["burnout_risk"]), use_container_width=True)
    with tabs[3]:
        markdown = plan_markdown(profile, prediction, plan, coaching)
        st.download_button("Download Markdown", markdown, file_name="daily_plan.md", mime="text/markdown")
        st.download_button("Download TXT", plan_text(profile, prediction, plan, coaching), file_name="daily_plan.txt", mime="text/plain")
        pdf_bytes = plan_pdf_bytes(profile, prediction, plan, coaching)
        if pdf_bytes:
            st.download_button("Download PDF", pdf_bytes, file_name="daily_plan.pdf", mime="application/pdf")
        else:
            st.caption("PDF export is enabled when `reportlab` is installed. Markdown and TXT exports are available now.")
else:
    st.info("Complete the check-in form to generate predictions, a schedule, and coaching notes.")
