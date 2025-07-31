from typing import List

# from fle.env.run_envs import get_local_container_ips
from fle.env.game.instance import FactorioInstance
from fle.env.game.game_state import GameState
from fle.commons.models.program import Program

class FactorioGameSession:
    instance: FactorioInstance
    game_state: GameState
    programs: List[Program]
    
    def __init__(self, instance: FactorioInstance, game_state: GameState):
        self.instance = instance
        self.game_state = game_state
