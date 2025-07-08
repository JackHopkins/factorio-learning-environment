from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from pydantic import BaseModel, Field

from fle.commons.models.timing_metrics import TimingMetrics

from fle.commons.models.achievements import ProductionFlows
from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState


class Program(BaseModel):
    id: Optional[int] = None
    code: str
    conversation: Conversation
    value: float = 0.0
    visits: int = 0
    parent_id: Optional[int] = None
    state: Optional[GameState] = None
    raw_reward: Optional[float] = None
    holdout_value: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    prompt_token_usage: Optional[int] = None
    completion_token_usage: Optional[int] = None
    token_usage: Optional[int] = None
    response: Optional[str] = None
    version: int = 1
    version_description: Optional[str] = ""
    model: str = "gpt-4o"
    meta: dict = {}
    achievements: dict = {}
    instance: int = -1
    depth: int = 0
    advantage: float = 0
    ticks: int = 0
    flows: Optional[ProductionFlows] = None
    timing_metrics: List[TimingMetrics] = Field(default_factory=list)

    def __repr__(self):
        return self.code

    def get_step(self):
        return int(((self.depth - 1) / 2) + 1)

    def get_uct(self, parent_visits: int, exploration_constant: float = 1.41) -> float:
        if self.visits == 0:
            return float("inf")
        return (self.value / self.visits) + exploration_constant * np.sqrt(
            np.log(parent_visits) / self.visits
        )

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    @classmethod
    def from_row(cls, row: Dict):
        return cls(
            id=row["id"],
            code=row["code"],
            conversation=Conversation.parse_raw(row["conversation_json"]),
            value=row["value"],
            visits=row["visits"],
            parent_id=row["parent_id"],
            state=GameState.parse(row["state_json"]) if row["state_json"] else None,
            raw_reward=row["raw_reward"],
            holdout_value=row["holdout_value"],
            created_at=row["created_at"],
            prompt_token_usage=row["prompt_token_usage"],
            completion_token_usage=row["completion_token_usage"],
            token_usage=row["token_usage"],
            response=row["response"],
            version=row["version"],
            version_description=row["version_description"],
            meta=row["meta"] if row["meta"] else {},
            achievements=row["achievements_json"] if row["achievements_json"] else {},
            instance=row["instance"],
            depth=row["depth"],
            advantage=row["advantage"],
            ticks=row["ticks"],
            timing_metrics=[
                TimingMetrics.parse_raw(m) for m in row["timing_metrics_json"]
            ]
            if row.get("timing_metrics_json")
            else [],
        )
