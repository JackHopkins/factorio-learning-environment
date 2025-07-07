import asyncio
import os
from typing import List, Dict

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import DictCursor

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.commons.db_client import DBClient
from fle.commons.models.program import Program
from fle.env import FactorioInstance

load_dotenv()


class BlueprintsToPrograms:
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

    def sample_scenarios(
        self, n_samples: int = 10, version: int = 17, skill_version: str = "v1.4"
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

            implementation = blueprint["implementation"]
            objective = blueprint["description"]
            if not objective.startswith('"""'):
                objective = f'"""\n{objective}\n"""'

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
                state=None,
                version=version,  # Set appropriate version
                version_description="Blueprint-based scenario seed",
            )

            programs.append(program)

        return programs

    def __del__(self):
        """Clean up database connection"""
        if hasattr(self, "conn"):
            self.conn.close()


async def save():
    instance = FactorioInstance(
        address="localhost",
        bounding_box=200,
        tcp_port=27000,
        cache_scripts=False,
        inventory={},
    )

    blueprints_to_programs = BlueprintsToPrograms(
        db_config={
            "host": os.getenv("SKILLS_DB_HOST"),
            "port": os.getenv("SKILLS_DB_PORT"),
            "dbname": os.getenv("SKILLS_DB_NAME"),
            "user": os.getenv("SKILLS_DB_USER"),
            "password": os.getenv("SKILLS_DB_PASSWORD"),
        },
        system_prompt=instance.get_system_prompt(),
    )

    scenarios = blueprints_to_programs.sample_scenarios(n_samples=1000)

    db_client = DBClient(
        **{
            "host": os.getenv("SKILLS_DB_HOST"),
            "port": os.getenv("SKILLS_DB_PORT"),
            "dbname": os.getenv("SKILLS_DB_NAME"),
            "user": os.getenv("SKILLS_DB_USER"),
            "password": os.getenv("SKILLS_DB_PASSWORD"),
        }
    )

    for scenario in scenarios:
        scenario.version = 19
        scenario.version_description = "Layout"
        await db_client.create_program(scenario)


if __name__ == "__main__":
    asyncio.run(save())
