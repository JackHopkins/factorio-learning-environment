from dataclasses import dataclass
from typing import Optional, Dict, Any

from fle.commons.models.game_state import GameState


@dataclass
class Action:
    """Action for the Factorio gym environment"""

    code: str
    agent_idx: int = 0
    game_state: Optional[GameState] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary format expected by the environment"""
        return {
            "code": self.code,
            "agent_idx": self.agent_idx,
            "game_state": self.game_state.to_raw() if self.game_state else None,
        }
