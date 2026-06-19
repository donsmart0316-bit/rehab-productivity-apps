from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.llm.prompt_templates import DAILY_PLAN_TEMPLATE, EXPLANATION_TEMPLATE, WEEKLY_PLAN_TEMPLATE


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    project_root = Path(__file__).resolve().parents[2]
    candidates = [
        project_root / ".env",
        project_root.parents[1] / ".env",
        project_root.parents[2] / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)


def llm_status() -> dict[str, str | bool]:
    _load_env_files()
    has_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"))
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    return {"provider": "Groq", "model": model, "key_loaded": has_key}


def _try_groq_llm():
    _load_env_files()
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    if not key:
        return None
    try:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            api_key=key,
            temperature=0.35,
            max_tokens=1200,
            timeout=20,
            max_retries=1,
        )
    except Exception:
        return None


def fallback_daily_explanation(user_profile: dict[str, Any], ml_predictions: dict[str, Any], plan: dict[str, Any]) -> str:
    schedule = plan.get("schedule", [])
    focus_blocks = plan.get("focus_blocks", [])
    breaks = plan.get("breaks", [])
    recovery = plan.get("recovery_interventions", [])
    lines = [
        f"# Daily Coaching Plan for {plan.get('date')}",
        "",
        f"Your plan is built around a predicted productivity score of {ml_predictions.get('productivity_score')} and {ml_predictions.get('burnout_risk')} burnout risk.",
        f"Recovery is currently estimated at {ml_predictions.get('recovery_score')}, so the schedule aims for useful output without borrowing too heavily from tomorrow.",
        "",
        "## Schedule",
    ]
    for item in schedule:
        lines.append(f"- {item['start']}-{item['end']}: {item['title']} ({item['item_type']}). {item['reason']}")
    lines.extend(["", "## Why This Works"])
    if focus_blocks:
        first = focus_blocks[0]
        lines.append(
            f"- `{first['title']}` is scheduled in your strongest focus window so difficult work happens when energy, recovery, and chronotype are most supportive."
        )
    if breaks:
        lines.append("- Breaks are treated as part of the plan because short recovery intervals help attention rebound and reduce physical strain from screen work.")
    if user_profile.get("fatigue_score", 0) >= 6 or ml_predictions.get("burnout_risk") in {"Medium", "High"}:
        lines.append("- Because fatigue or burnout risk is elevated, the plan avoids stacking demanding tasks back-to-back and gives recovery more authority.")
    lines.extend(["", "## Recovery Advice"])
    for intervention in recovery[:4]:
        lines.append(f"- {intervention['type']}: {intervention.get('details', '')}")
    return "\n".join(lines)


def fallback_weekly_explanation(weekly_context: dict[str, Any], plans: dict[str, Any]) -> str:
    lines = [
        "# Weekly Coaching Plan",
        "",
        "Use the primary plan on normal days, the conservative plan after poor sleep or high stress, and the high-performance plan only when recovery and burnout risk are favorable.",
        "",
        "## Weekly Priorities",
        "- Protect deep work windows for the highest-value tasks.",
        "- Keep meetings in moderate-energy periods.",
        "- Treat recovery blocks as part of the workload, not optional extras.",
        "",
        "## Burnout Prevention",
        "- Watch sleep debt, fatigue, and cumulative load. If two rise together, switch to the conservative plan.",
    ]
    return "\n".join(lines)


def generate_daily_coaching_text(user_profile: dict[str, Any], ml_predictions: dict[str, Any], plan: dict[str, Any]) -> str:
    llm = _try_groq_llm()
    if llm is None:
        return fallback_daily_explanation(user_profile, ml_predictions, plan)
    prompt = DAILY_PLAN_TEMPLATE.format(
        user_profile=json.dumps(user_profile, indent=2),
        ml_predictions=json.dumps(ml_predictions, indent=2),
        plan=json.dumps(plan, indent=2),
    )
    try:
        return llm.invoke(prompt).content
    except Exception:
        return fallback_daily_explanation(user_profile, ml_predictions, plan)


def generate_weekly_coaching_text(weekly_context: dict[str, Any], plans: dict[str, Any]) -> str:
    llm = _try_groq_llm()
    if llm is None:
        return fallback_weekly_explanation(weekly_context, plans)
    prompt = WEEKLY_PLAN_TEMPLATE.format(
        weekly_context=json.dumps(weekly_context, indent=2),
        plans=json.dumps(plans, indent=2),
    )
    try:
        return llm.invoke(prompt).content
    except Exception:
        return fallback_weekly_explanation(weekly_context, plans)


def explain_schedule_item(user_profile: dict[str, Any], rule_outputs: dict[str, Any], schedule_item: dict[str, Any]) -> str:
    llm = _try_groq_llm()
    if llm is None:
        risk = user_profile.get("predicted_burnout_risk") or user_profile.get("burnout_risk") or "current"
        return (
            f"{schedule_item.get('title')} was placed at {schedule_item.get('start')} because it fits your energy pattern, recovery needs, "
            f"and {risk} burnout context. {schedule_item.get('reason')}"
        )
    prompt = EXPLANATION_TEMPLATE.format(
        user_profile=json.dumps(user_profile, indent=2),
        rule_outputs=json.dumps(rule_outputs, indent=2),
        schedule_item=json.dumps(schedule_item, indent=2),
    )
    try:
        return llm.invoke(prompt).content
    except Exception:
        risk = user_profile.get("predicted_burnout_risk") or user_profile.get("burnout_risk") or "current"
        return (
            f"{schedule_item.get('title')} was placed at {schedule_item.get('start')} because it fits your energy pattern, recovery needs, "
            f"and {risk} burnout context. {schedule_item.get('reason')}"
        )
