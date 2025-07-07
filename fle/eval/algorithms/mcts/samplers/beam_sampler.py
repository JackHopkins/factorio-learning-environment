import random
from typing import Optional

import psycopg2
import tenacity
from psycopg2.extras import DictCursor
from tenacity import retry_if_exception_type, wait_exponential

from fle.commons.db_client import DBClient
from fle.eval.algorithms.mcts.samplers.db_sampler import DBSampler
from fle.commons.models.program import Program


class BeamSampler(DBSampler):
    """
    Beam Search sampler that maintains a beam of the best performing programs.
    It selects parents from the top N programs based on their values.

    Args:
        db_client: Database client to get programs
        beam_width: Number of top programs to maintain in the beam
        max_conversation_length: Maximum allowed conversation length
        exploration_prob: Probability of selecting a random program instead of from beam
    """

    def __init__(
        self,
        db_client: DBClient,
        beam_width: int = 5,
        max_conversation_length: int = 20,
        exploration_prob: float = 0.1,
    ):
        super().__init__(db_client)
        self.beam_width = beam_width
        self.max_conversation_length = max_conversation_length
        self.exploration_prob = exploration_prob

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def sample_parent(
        self, version: int = 1, update_visits: bool = False
    ) -> Optional[Program]:
        """
        Note: update_visits parameter is ignored for beam sampling since
        visit statistics are not relevant for beam search selection
        """
        """
        Sample a parent program from the current beam or exploration set.

        Args:
            version: The version of programs to sample from

        Returns:
            A sampled Program or None if no valid programs exist
        """
        max_assistant_length = (self.max_conversation_length * 2) + 1

        try:
            with self.db_client.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # Decide whether to explore or exploit
                    if random.random() < self.exploration_prob:
                        # Exploration: Sample from recent programs outside the beam
                        cur.execute(
                            """
                            WITH beam AS (
                                SELECT id
                                FROM programs 
                                WHERE version = %s
                                AND value IS NOT NULL
                                AND jsonb_array_length(conversation_json->'messages') < %s
                                ORDER BY value DESC
                                LIMIT %s
                            ),
                            exploration_candidates AS (
                                SELECT id 
                                FROM programs
                                WHERE version = %s
                                AND value IS NOT NULL
                                AND jsonb_array_length(conversation_json->'messages') < %s
                                AND id NOT IN (SELECT id FROM beam)
                                ORDER BY created_at DESC
                                LIMIT 100
                            )
                            SELECT id FROM exploration_candidates
                            ORDER BY RANDOM()
                            LIMIT 1
                        """,
                            (
                                version,
                                max_assistant_length,
                                self.beam_width,
                                version,
                                max_assistant_length,
                            ),
                        )
                    else:
                        # Exploitation: Sample from the beam (top N programs)
                        cur.execute(
                            """
                            WITH beam AS (
                                SELECT id, value
                                FROM programs 
                                WHERE version = %s
                                AND value IS NOT NULL
                                AND jsonb_array_length(conversation_json->'messages') < %s
                                ORDER BY value DESC
                                LIMIT %s
                            )
                            SELECT id FROM beam
                            ORDER BY RANDOM()
                            LIMIT 1
                        """,
                            (version, max_assistant_length, self.beam_width),
                        )

                    result = cur.fetchone()
                    if not result:
                        return None

                    # Fetch the complete program
                    cur.execute(
                        """
                        SELECT * FROM programs WHERE id = %s
                    """,
                        (result["id"],),
                    )

                    row = cur.fetchone()
                    return Program.from_row(dict(row)) if row else None

        except Exception as e:
            print(f"Error sampling parent: {e}")
            raise e

    async def get_beam_stats(self, version: int = 1) -> dict:
        """
        Get statistics about the current beam.

        Args:
            version: The version to get stats for

        Returns:
            Dictionary containing beam statistics
        """
        try:
            with self.db_client.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        """
                        WITH beam AS (
                            SELECT value
                            FROM programs 
                            WHERE version = %s
                            AND value IS NOT NULL
                            ORDER BY value DESC
                            LIMIT %s
                        )
                        SELECT 
                            COUNT(*) as beam_size,
                            AVG(value) as mean_value,
                            MIN(value) as min_value,
                            MAX(value) as max_value
                        FROM beam
                    """,
                        (version, self.beam_width),
                    )

                    result = cur.fetchone()
                    return dict(result) if result else {}

        except Exception as e:
            print(f"Error getting beam stats: {e}")
            return {}
