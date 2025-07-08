import asyncio
import os
from dotenv import load_dotenv

from fle.commons.db_client import DBClient
from fle.env import FactorioInstance

# Load environment variables
load_dotenv()


async def evaluate_program_trace(version: int = 330) -> None:
    """
    Load and evaluate a program trace from the database.

    Args:
        version: The version number to fetch from the database
    """
    # Initialize database client
    db_client = DBClient(
        max_conversation_length=100,  # Assuming default max conversation length
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )

    # Create Factorio instance using pytest fixture
    def game_instance():
        try:
            instance = FactorioInstance(
                address="localhost",
                bounding_box=200,
                tcp_port=27000,
                cache_scripts=False,
                fast=False,
                inventory={},
            )
            instance.speed(20)
            return instance
        except Exception as e:
            raise e

    # Get the instance
    instance = game_instance()
    instance.reset()

    # 96269 (potentially okay)
    # 100778 (same)

    # Execute SQL query to get program trace
    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH RECURSIVE program_trace AS (
                    -- Base case: start with most recent program
                    SELECT
                        value,
                        code,
                        response,
                        id,
                        parent_id,
                        created_at,
                        instance
                    FROM (
                        SELECT value, code, response, id, parent_id, created_at, instance
                        FROM programs
                        WHERE id = 96269
                    ) latest

                    UNION ALL

                    -- Recursive case: get the parent program
                    SELECT
                        p.value,
                        p.code,
                        p.response,
                        p.id,
                        p.parent_id,
                        p.created_at,
                        p.instance
                    FROM programs p
                    INNER JOIN program_trace pt ON p.id = pt.parent_id
                )
                SELECT
                    value,
                    code,
                    response,
                    id,
                    parent_id,
                    created_at,
                    instance
                FROM program_trace
                ORDER BY created_at ASC;
            """)

            traces = cur.fetchall()

    # Evaluate each code snippet in the trace
    print(f"Found {len(traces)} entries in the program trace")
    for i, trace in enumerate(traces):
        code = trace[1]  # code is the second column
        print(f"\nEvaluating trace {i + 1}/{len(traces)}")
        print(f"Program ID: {trace[3]}")  # id is the fourth column

        try:
            # Evaluate the code
            reward, _, result = instance.eval(code, timeout=30)
            print("Evaluation result:")
            print(f"Reward: {reward}")
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error evaluating code: {e}")
            continue


if __name__ == "__main__":
    # Run the async function
    asyncio.run(evaluate_program_trace())
