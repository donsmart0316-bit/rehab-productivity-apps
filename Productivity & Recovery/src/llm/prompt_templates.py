from __future__ import annotations

try:
    from langchain_core.prompts import ChatPromptTemplate
except Exception:
    ChatPromptTemplate = None


DAILY_PLAN_TEMPLATE = """You are an AI Productivity & Recovery Coach.
Explain the daily plan using only the structured schedule and rule outputs provided.
Do not invent new schedule items.

User profile:
{user_profile}

ML predictions:
{ml_predictions}

Recommendation plan:
{plan}

Write:
1. A concise daily coaching plan.
2. Why the most demanding tasks are placed where they are.
3. Recovery advice.
4. Burnout-protection guidance.
Use a calm, practical, human tone.
"""


WEEKLY_PLAN_TEMPLATE = """You are an AI Productivity & Recovery Coach.
Use the provided daily plans and predictions to explain weekly priorities.
Do not invent tasks or schedule items.

Weekly context:
{weekly_context}

Plans:
{plans}

Write:
1. Weekly priorities.
2. Recovery strategy.
3. Burnout prevention guidance.
4. Productivity insights.
"""


EXPLANATION_TEMPLATE = """Explain why this recommendation was made.

User state:
{user_profile}

Rule outputs:
{rule_outputs}

Schedule item:
{schedule_item}

Give a short explanation grounded in physiology, workload, recovery, and circadian timing.
"""


def daily_plan_prompt():
    if ChatPromptTemplate is None:
        return DAILY_PLAN_TEMPLATE
    return ChatPromptTemplate.from_template(DAILY_PLAN_TEMPLATE)


def weekly_plan_prompt():
    if ChatPromptTemplate is None:
        return WEEKLY_PLAN_TEMPLATE
    return ChatPromptTemplate.from_template(WEEKLY_PLAN_TEMPLATE)


def explanation_prompt():
    if ChatPromptTemplate is None:
        return EXPLANATION_TEMPLATE
    return ChatPromptTemplate.from_template(EXPLANATION_TEMPLATE)

