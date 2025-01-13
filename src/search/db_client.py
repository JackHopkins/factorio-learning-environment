import json
import math
import random
import statistics
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import psycopg2
import tenacity
from psycopg2.extras import DictCursor
from tenacity import wait_exponential, retry_if_exception_type, wait_random_exponential
from search.model.program import Program


class DBClient:
    def __init__(self, max_conversation_length: int = 20, **db_config):
        self.db_config = db_config
        self.max_conversation_length = max_conversation_length
        # Don't store connection as instance variable
        # Instead create connection pool
        self.pool = []
        self.max_pool_size = 5

    @contextmanager
    def get_connection(self):
        """Context manager to handle database connections"""
        conn = None
        try:
            # Try to get connection from pool
            if self.pool:
                conn = self.pool.pop()
                try:
                    # Test if connection is still alive
                    conn.cursor().execute('SELECT 1')
                except (psycopg2.OperationalError, psycopg2.InterfaceError):
                    # If connection is dead, close it and create new one
                    conn.close()
                    conn = None

            # If no connection from pool, create new one
            if conn is None:
                conn = psycopg2.connect(**self.db_config)

            yield conn

            # If connection still good, return to pool
            try:
                conn.cursor().execute('SELECT 1')
                if len(self.pool) < self.max_pool_size:
                    self.pool.append(conn)
                else:
                    conn.close()
            except:
                conn.close()

        except Exception as e:
            if conn:
                conn.close()
            raise e

    @tenacity.retry(
        retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError)),
        wait=wait_random_exponential(multiplier=1, min=4, max=10))
    async def create_program(self, program: Program) -> Program:
        """Create a new program, now with connection management"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO programs (code, value, visits, parent_id, state_json, conversation_json, 
                                           completion_token_usage, prompt_token_usage, token_usage, response, 
                                           holdout_value, raw_reward, version, version_description, model, meta, 
                                           achievements_json, instance, depth, advantage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                    """, (program.code, program.value, 0, program.parent_id,
                          program.state.to_raw() if program.state else None,
                          json.dumps(program.conversation.dict()),
                          program.completion_token_usage,
                          program.prompt_token_usage,
                          program.token_usage,
                          program.response,
                          program.holdout_value,
                          program.raw_reward,
                          program.version,
                          program.version_description,
                          program.model,
                          json.dumps(program.meta),
                          json.dumps(program.achievements),
                          program.instance,
                          program.depth/2,
                          program.advantage
                          ))

                    id, created_at = cur.fetchone()
                    conn.commit()
                    program.id = id
                    program.created_at = created_at
                    return program
        except Exception as e:
            print(f"Error creating program: {e}")
            raise e

    @tenacity.retry(retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError)),
                    wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_all_program_rewards(self, version: int = None) -> List[float]:
        """Get all program rewards with proper connection management"""
        query = """
            SELECT value 
            FROM programs 
            WHERE value IS NOT NULL
        """
        if version is not None:
            query += " AND version = %s"

        params = (version,) if version is not None else ()

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query.strip(), params)
                    results = cur.fetchall()
                    return [row[0] for row in results]
        except Exception as e:
            print(f"Error fetching program rewards: {e}")
            return []

    @tenacity.retry(retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError)),
                    wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_largest_version(self) -> int:
        query = """
            SELECT MAX(version)
            FROM programs
        """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error fetching largest version: {e}")

    async def get_largest_depth_in_version(self, version):
        query = f"""
                    SELECT MAX(depth)
                    FROM programs
                    WHERE version = {version}
                """

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    result = cur.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            print(f"Error fetching largest version: {e}")


    @tenacity.retry(retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError)),
                    wait=wait_random_exponential(multiplier=1, min=4, max=10))
    async def sample_parent(self, version=1, compression_strength: Optional[float] = None,
                            adaptive_period: int = 100) -> Optional[Program]:
        """
        Sample parent with proper connection management and adjusted reward scaling.

        Args:
            version: The version of programs to sample from
            compression_strength: Fixed compression strength between 0 and 1.
                                If None, uses adaptive compression. Higher values mean more exploitation. Lower means more exploration.
            adaptive_period: Number of steps for a full sine wave cycle when using
                            adaptive compression.
        """
        max_assistant_length = (self.max_conversation_length * 2) + 1

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # First get the current step count for adaptive compression
                    if compression_strength is None:
                        cur.execute(f"SELECT COUNT(*) as step_count FROM programs WHERE version = {version}")
                        step_count = cur.fetchone()['step_count']
                        # Calculate adaptive compression using sine wave
                        # sin goes from -1 to 1, so we transform to 0 to 1
                        compression_strength = (math.sin(2 * math.pi * step_count / adaptive_period) + 1) / 2

                    cur.execute("""
                        WITH recent AS (
                            SELECT id, value, conversation_json
                            FROM programs
                            WHERE version = %s 
                            AND advantage IS NOT NULL
                            -- AND jsonb_array_length(conversation_json->'messages') < %s
                            ORDER BY created_at DESC
                            LIMIT 300
                        )
                        SELECT id, advantage 
                        FROM recent
                        """, (version)) #, max_assistant_length))

                    results = cur.fetchall()
                    if not results:
                        return None

                    # Get statistics of the value distribution
                    values = [row['advantage'] for row in results]
                    mean_value = statistics.mean(values)
                    std_value = statistics.stdev(values) if len(values) > 1 else 1.0

                    # Apply reward transformation to handle power-law distribution
                    def transform_reward(value):
                        # Z-score normalization
                        z_score = (value - mean_value) / std_value if std_value > 0 else 0

                        # Compress extreme values using tanh with current compression strength
                        compressed = math.tanh(z_score * compression_strength)

                        # Scale back to positive values and add small epsilon
                        return (compressed + 1.0) / 2.0 + 1e-6

                    # Log current compression state
                    print(f"Using compression strength: {compression_strength:.3f} "
                          f"({'adaptive' if compression_strength is None else 'fixed'})")

                    # Calculate transformed weights
                    weights = [
                        (row['id'], transform_reward(row['advantage']))
                        for row in results
                    ]

                    # Normalize weights
                    total_weight = sum(w[1] for w in weights)
                    if total_weight == 0:
                        sampled_id = random.choice([w[0] for w in weights])
                    else:
                        normalized_weights = [(id, w / total_weight) for id, w in weights]
                        sampled_id = random.choices(
                            [id for id, _ in normalized_weights],
                            weights=[w for _, w in normalized_weights],
                            k=1
                        )[0]

                    # Fetch the selected program
                    cur.execute("""
                        SELECT * FROM programs WHERE id = %s
                        """, (sampled_id,))

                    row = cur.fetchone()
                    return Program.from_row(dict(row)) if row else None
        except Exception as e:
            print(f"Error sampling parent: {e}")
            raise e

    @tenacity.retry(retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError)),
                    wait=wait_random_exponential(multiplier=1, min=4, max=10))
    async def get_parent_visit_stats(self, version: int = None) -> Dict[str, float]:
        """Get visit statistics with proper connection management"""
        query = """
            SELECT 
                AVG(visits) as avg_visits,
                MIN(visits) as min_visits,
                MAX(visits) as max_visits,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY visits) as median_visits
            FROM programs 
            WHERE visits > 0
        """
        if version is not None:
            query += " AND version = %s"

        params = (version,) if version is not None else ()

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    return {
                        'avg_visits': result[0],
                        'min_visits': result[1],
                        'max_visits': result[2],
                        'median_visits': result[3]
                    }
        except Exception as e:
            print(f"Error fetching visit statistics: {e}")
            return {}

    async def update_program(self, program_id: int, updates: Dict[str, Any]) -> Program:
        """Update program with proper connection management"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    set_clauses = [f"{k} = %s" for k in updates.keys()]
                    values = list(updates.values())

                    cur.execute(f"""
                        UPDATE programs
                        SET {', '.join(set_clauses)}
                        WHERE id = %s
                        RETURNING *
                    """, values + [program_id])

                    conn.commit()
                    row = cur.fetchone()
                    return Program.from_row(dict(zip([desc[0] for desc in cur.description], row)))
        except Exception as e:
            print(f"Error updating program: {e}")
            raise e
