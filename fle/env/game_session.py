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
        
    async def create_factorio_instance(
        instance_id: int, num_agents: int = 1, agent_cards: Optional[List[AgentCard]] = None
    ) -> FactorioInstance:
        """Create and asynchronously initialize a single Factorio instance"""
        ips, udp_ports, tcp_ports = get_local_container_ips()

        common_kwargs = {
            "address": ips[instance_id],
            "tcp_port": tcp_ports[instance_id],
            "bounding_box": 200,
            "fast": True,
            "cache_scripts": True,
            "inventory": {},
            "all_technologies_researched": True,
            "num_agents": num_agents,
        }

        if num_agents > 1:
            instance = await A2AFactorioInstance.create(
                **common_kwargs, agent_cards=agent_cards
            )
        else:
            instance = FactorioInstance(**common_kwargs)

        instance.set_speed(10)
        return instance
        

async def run_trajectory(process_id: int, config: EvalConfig):
    """Entry point for running a single trajectory"""
    db_client = await create_db_client()
    instance = await create_factorio_instance(
        process_id, len(config.agents), config.agent_cards
    )
    evaluator = SimpleFactorioEvaluator(
        db_client=db_client, instance=instance, value_accrual_time=1, error_penalty=0
    )
    task = config.task
    task.setup(instance)

    runner = TrajectoryRunner(config.agents, db_client, evaluator, config, process_id)

    await runner.run()
    await db_client.cleanup()

async def get_next_version() -> int:
    """Get next available version number"""
    db_client = await create_db_client()
    version = await db_client.get_largest_version()
    await db_client.cleanup()
    return version + 1
