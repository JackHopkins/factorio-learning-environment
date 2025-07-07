from typing import List, Optional, Tuple, Dict

import psycopg2
from psycopg2.extras import DictCursor

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.commons.models.game_state import GameState
from fle.commons.models.program import Program
from fle.env import FactorioInstance


class BlueprintScenarioSampler:
    """Samples scenarios from existing Factorio blueprint implementations in the `skills` table."""

    def __init__(self, db_config: Dict[str, str], system_prompt: str):
        """
        Initialize the blueprint sampler

        Args:
            db_config: Database configuration for skills DB
            system_prompt: System prompt for the conversation
        """
        self.db_config = db_config
        self.system_prompt = system_prompt
        self.conn = psycopg2.connect(**db_config)

    def _get_blueprint_scenarios(
        self, limit: int = 100, version: str = "v1.4"
    ) -> List[Dict]:
        """Get blueprint scenarios from skills database"""
        query = """
            SELECT description, implementation, score, complexity, dependencies
            FROM skills
            WHERE implementation IS NOT NULL 
            AND description IS NOT NULL
            AND version = %s
            ORDER BY RANDOM()
            LIMIT %s
        """

        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                query,
                (
                    version,
                    limit,
                ),
            )
            return [dict(row) for row in cur.fetchall()]

    def _prepare_scenario(
        self, instance: FactorioInstance, blueprint: Dict, inventory: Dict
    ) -> Tuple[Optional[GameState], str, str]:
        """
        Prepare a scenario from a blueprint implementation

        Returns:
            Tuple of (game_state, objective, implementation)
        """
        try:
            # Reset instance to clean state
            instance.reset()
            instance.set_inventory(inventory)

            # Run the implementation to set up initial state
            reward, _, result = instance.eval(blueprint["implementation"], timeout=30)

            if "error" in result.lower():
                raise Exception("Could not initialise scenario")

            # Capture the game state
            game_state = GameState.from_instance(instance)

            # Format objective from description
            objective = blueprint["description"]
            if not objective.startswith('"""'):
                objective = f'"""\n{objective}\n"""'

            return game_state, objective, blueprint["implementation"]

        except Exception as e:
            print(f"Error preparing scenario: {str(e)}")
            raise e

    async def sample_scenarios(
        self,
        instance: FactorioInstance,
        n_samples: int = 10,
        version: int = 17,
        skill_version: str = "v1.4",
    ) -> List[Program]:
        """
        Sample scenarios and create seed programs

        Args:
            instance: Factorio instance for state setup
            n_samples: Number of scenarios to sample

        Returns:
            List of Program objects ready for seeding
        """
        # Get blueprint scenarios
        blueprints = self._get_blueprint_scenarios(
            limit=n_samples, version=skill_version
        )

        programs = []

        for blueprint in blueprints:
            # Parse depenencies into inventory object
            dependencies = blueprint["dependencies"]
            inventory = {}
            for dependency in dependencies:
                item, count = dependency.strip().split(":")
                inventory[item.strip("'")] = int(count)

            # Prepare scenario
            try:
                game_state, objective, implementation = self._prepare_scenario(
                    instance, blueprint, inventory
                )
            except Exception:
                continue

            if not game_state:
                continue

            # Create conversation context
            conversation = Conversation(
                messages=[
                    Message(role="system", content=self.system_prompt),
                    Message(role="user", content=f"Starting Inventory: {inventory}"),
                    Message(role="assistant", content=objective),
                    Message(role="user", content="Execution result: \n"),
                    Message(role="assistant", content=implementation.strip()),
                ]
            )

            # Create seed program
            program = Program(
                id=hash((objective, str(conversation.messages))),
                code=implementation.strip(),
                conversation=conversation,
                value=float(blueprint["score"]),  # Use skill score as initial value
                state=game_state,
                version=version,  # Set appropriate version
                version_description="Blueprint-based scenario seed",
            )

            programs.append(program)

        return programs

    def __del__(self):
        """Clean up database connection"""
        if hasattr(self, "conn"):
            self.conn.close()
