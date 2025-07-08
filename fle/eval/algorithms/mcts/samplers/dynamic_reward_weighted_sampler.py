import math
import random
import statistics
from typing import Optional

import psycopg2
import tenacity
from psycopg2.extras import DictCursor
from tenacity import retry_if_exception_type, wait_exponential

from fle.commons.db_client import DBClient
from fle.commons.models.program import Program

from .db_sampler import DBSampler


class DynamicRewardWeightedSampler(DBSampler):
    """
    Dynamic Reward-Weighted Sampler, which samples parents based on their reward scores,
    adjusted by a dynamic scaling factor that changes over time to balance exploration and exploitation.

    The adaptive compression strength acts like a dynamic temperature parameter that automatically cycles
    between exploration (high compression) and exploitation (low compression) phases.

    Args:
        db_client: Database client to get programs
        compression_strength: Fixed compression strength between 0 and 1.
                                    If None, uses adaptive compression. Lower values mean more exploitation. Higher means more exploration.
        adaptive_period: Number of steps for a full sine wave cycle when using adaptive compression.
    """

    def __init__(
        self,
        db_client: DBClient,
        compression_strength=None,
        max_conversation_length=20,
        adaptive_period=200,
        maximum_lookback=20,
    ):
        super().__init__(db_client, maximum_lookback)
        self.max_conversation_length = max_conversation_length
        self.db_client = db_client
        self.compression_strength = compression_strength
        self.adaptive_period = adaptive_period

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def sample_parent(self, version=1) -> Optional[Program]:
        """
        Sample parent with adjusted reward scaling.

        Args:
            version: The version of programs to sample from
            compression_strength: Fixed compression strength between 0 and 1.
                                If None, uses adaptive compression. Higher values mean more exploitation. Lower means more exploration.
            adaptive_period: Number of steps for a full sine wave cycle when using
                            adaptive compression.
        """
        try:
            with self.db_client.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # First get the current step count for adaptive compression
                    if self.compression_strength is None:
                        cur.execute(
                            f"SELECT COUNT(*) as step_count FROM programs WHERE version = {version}"
                        )
                        step_count = cur.fetchone()["step_count"]
                        # Calculate adaptive compression using sine wave
                        # sin goes from -1 to 1, so we transform to 0 to 1
                        compression_strength = (
                            math.sin(2 * math.pi * step_count / self.adaptive_period)
                            + 1
                        ) / 2
                    else:
                        compression_strength = self.compression_strength

                    cur.execute(
                        f"""select max(depth) from programs where version = {version}"""
                    )
                    max_depth = cur.fetchone()["max"]
                    if not max_depth:
                        max_depth = 0
                    min_depth = max(0, max_depth - self.maximum_lookback)

                    cur.execute(
                        """
                                WITH recent AS (
                                    SELECT id, advantage, conversation_json
                                    FROM programs
                                    WHERE version = %s 
                                    AND advantage IS NOT NULL
                                    AND depth > %s
                                    ORDER BY created_at DESC
                                    LIMIT 300
                                )
                                SELECT id, advantage 
                                FROM recent
                                """,
                        (version, min_depth),
                    )

                    results = cur.fetchall()
                    if not results:
                        return None

                    # Get statistics of the value distribution
                    values = [row["advantage"] for row in results]
                    mean_value = statistics.mean(values)
                    std_value = statistics.stdev(values) if len(values) > 1 else 1.0

                    # Apply reward transformation to handle power-law distribution
                    def transform_reward(value):
                        # Z-score normalization
                        z_score = (
                            (value - mean_value) / std_value if std_value > 0 else 0
                        )

                        # Compress extreme values using tanh with current compression strength
                        compressed = math.tanh(z_score * compression_strength)

                        # Scale back to positive values and add small epsilon
                        return (compressed + 1.0) / 2.0 + 1e-6

                    # Log current compression state
                    if compression_strength:
                        print(f"Using compression strength: {compression_strength:.3f}")
                    else:
                        print("Using adaptive compression strength")

                    # Calculate transformed weights
                    weights = [
                        (row["id"], transform_reward(row["advantage"]))
                        for row in results
                    ]

                    # Normalize weights
                    total_weight = sum(w[1] for w in weights)
                    if total_weight == 0:
                        sampled_id = random.choice([w[0] for w in weights])
                    else:
                        normalized_weights = [
                            (id, w / total_weight) for id, w in weights
                        ]
                        sampled_id = random.choices(
                            [id for id, _ in normalized_weights],
                            weights=[w for _, w in normalized_weights],
                            k=1,
                        )[0]

                    # Fetch the selected program
                    cur.execute(
                        """
                                SELECT * FROM programs WHERE id = %s
                                """,
                        (sampled_id,),
                    )

                    row = cur.fetchone()
                    if row:
                        program = Program.from_row(dict(row))
                        return program
                    return None

        except Exception as e:
            print(f"Error sampling parent: {e}")
            raise e
