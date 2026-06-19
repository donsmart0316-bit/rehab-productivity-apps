from __future__ import annotations

import os
from pathlib import Path


def _load_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    project_root = Path(__file__).resolve().parents[2]
    for path in [project_root / ".env", project_root.parents[1] / ".env", project_root.parents[2] / ".env"]:
        if path.exists():
            load_dotenv(path, override=False)


def daily_coaching(profile: dict, prediction: dict, plan: dict) -> str:
    from src.llm import planner_chain

    return planner_chain.generate_daily_coaching_text(profile, prediction, plan)


def weekly_coaching(context: dict, plans: dict) -> str:
    from src.llm import planner_chain

    return planner_chain.generate_weekly_coaching_text(context, plans)


def provider_status() -> dict[str, str | bool]:
    _load_env_files()
    has_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"))
    return {"provider": "Groq", "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), "key_loaded": has_key}
