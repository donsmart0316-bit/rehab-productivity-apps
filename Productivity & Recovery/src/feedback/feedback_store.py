from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class FeedbackRecord:
    user_id: str
    date: str
    recommended_plan: dict[str, Any]
    actual_plan_followed: dict[str, Any] | None = None
    user_satisfaction_rating: int | None = None
    perceived_productivity: int | None = None
    perceived_fatigue: int | None = None
    comments: str | None = None


class FeedbackStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: FeedbackRecord) -> None:
        row = asdict(record)
        row["recommended_plan"] = json.dumps(row["recommended_plan"])
        row["actual_plan_followed"] = json.dumps(row["actual_plan_followed"] or {})
        frame = pd.DataFrame([row])
        if self.path.exists():
            frame.to_csv(self.path, mode="a", header=False, index=False)
        else:
            frame.to_csv(self.path, index=False)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            return pd.DataFrame()
        return pd.read_csv(self.path)

