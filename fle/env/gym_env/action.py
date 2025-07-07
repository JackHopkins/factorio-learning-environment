from dataclasses import dataclass
from typing import Optional, Dict, Any

from fle.commons.models.game_state import GameState


@dataclass
class Action:
    """Action for the Factorio gym environment"""

    agent_idx: int
    code: str
    game_state: Optional[GameState]

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary format expected by the environment"""
        return {
            "agent_idx": self.agent_idx,
            "code": self.code,
            "game_state": self.game_state.to_raw() if self.game_state else "",
        }
