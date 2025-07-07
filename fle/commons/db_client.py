import json
import logging
import math
import os
import random
import sqlite3
import statistics
import threading
from abc import ABC
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2
import tenacity
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool
from tenacity import retry_if_exception_type, wait_exponential, wait_random_exponential

from fle.commons.models.conversation import Conversation
from fle.commons.models.game_state import GameState
from fle.commons.models.program import Program

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DBClient(ABC):
    def __init__(
        self,
        max_conversation_length: int = 20,
        min_connections: int = 5,
        max_connections: int = 20,
        **db_config,
    ):
        self.max_conversation_length = max_conversation_length
        # Don't store connection as instance variable
        # Instead create connection pool
        # self.pool = []
        # self.max_pool_size = 5
        self._pool = None
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._lock = threading.Lock()
        self.db_config = db_config

    async def initialize(self):
        """Initialize the connection pool"""
        pass

    @contextmanager
    def get_connection(self):
        """Regular context manager for database connections"""
        pass

    async def get_beam_heads(self, version: int, beam_width: int) -> List[Program]:
        """Get the highest value programs across all depths for a given version."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # Use a CTE to get diverse set of programs
                    cur.execute(
                        """
                        WITH ProgramsByDepth AS (
                            SELECT DISTINCT ON (depth) *
                            FROM programs
                            WHERE version = %s
                            AND state_json IS NOT NULL
                            AND value IS NOT NULL
                            ORDER BY depth, value DESC
                        )
                        SELECT * FROM (
                            SELECT * FROM ProgramsByDepth
                            ORDER BY value DESC
                            LIMIT %s
                        ) as depth_diverse
                        UNION DISTINCT
                        SELECT * FROM (
                            SELECT * FROM programs
                            WHERE version = %s
                            AND state_json IS NOT NULL
                            AND value IS NOT NULL
                            ORDER BY value DESC
                            LIMIT %s
                        ) as value_focused
                        ORDER BY value DESC
                        LIMIT %s
                    """,
                        (version, beam_width, version, beam_width * 2, beam_width),
                    )

                    results = cur.fetchall()
                    if not results:
                        logger.warning(f"No programs found for version {version}")
                        return []

                    programs = [Program.from_row(dict(row)) for row in results]
                    depths = [p.depth for p in programs]
                    logger.info(
                        f"Found {len(programs)} beam heads for version {version} - {depths}"
                    )
                    return programs
        except Exception as e:
            logger.error(f"Error fetching beam heads: {e}", exc_info=True)
            return []

    async def version_exists(self, version: int) -> bool:
        """Check if a version exists in the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS(
                            SELECT 1 FROM programs WHERE version = %s
                        )
                    """,
                        (version,),
                    )
                    return cur.fetchone()[0]
        except Exception as e:
            print(f"Error checking version existence: {e}")
            return False

    async def get_version_metadata(self, version: int) -> dict:
        """Get metadata for a specific version"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        """
                        SELECT DISTINCT version_description, model
                        FROM programs 
                        WHERE version = %s
                        LIMIT 1
                    """,
                        (version,),
                    )
                    result = cur.fetchone()
                    return dict(result) if result else {}
        except Exception as e:
            print(f"Error fetching version metadata: {e}")
            return {}

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError)
        ),
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
    )
    async def create_program(self, program: Program) -> Program:
        """Create a new program, now with connection management"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO programs (code, value, visits, parent_id, state_json, conversation_json, 
                                           completion_token_usage, prompt_token_usage, token_usage, response, 
                                           holdout_value, raw_reward, version, version_description, model, meta, 
                                           achievements_json, instance, depth, advantage, ticks, timing_metrics_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                    """,
                        (
                            program.code,
                            program.value,
                            0,
                            program.parent_id,
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
                            program.depth / 2,
                            program.advantage,
                            program.ticks,
                            json.dumps(program.timing_metrics)
                            if program.timing_metrics
                            else None,
                        ),
                    )

                    id, created_at = cur.fetchone()
                    conn.commit()
                    program.id = id
                    program.created_at = created_at
                    return program
        except Exception as e:
            conn.rollback()
            print(f"Error creating program: {e}")
            raise e

    async def cleanup(self):
        """Clean up database resources"""
        if self._pool is not None:
            with self._lock:
                if self._pool is not None:
                    try:
                        self._pool.closeall()
                    except Exception as e:
                        logger.error(f"Error closing connection pool: {e}")
                    finally:
                        self._pool = None

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
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

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
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
                    return result[0] if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error fetching largest version: {e}")
            return 0

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
                    return result[0] if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error fetching largest depth: {e}")
            return 0

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
    )
    async def sample_parent(
        self,
        version=1,
        compression_strength: Optional[float] = None,
        adaptive_period: int = 100,
    ) -> Optional[Program]:
        """
        Sample parent with proper connection management and adjusted reward scaling.

        Args:
            version: The version of programs to sample from
            compression_strength: Fixed compression strength between 0 and 1.
                                If None, uses adaptive compression. Higher values mean more exploitation. Lower means more exploration.
            adaptive_period: Number of steps for a full sine wave cycle when using
                            adaptive compression.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    # First get the current step count for adaptive compression
                    if compression_strength is None:
                        cur.execute(
                            f"SELECT COUNT(*) as step_count FROM programs WHERE version = {version}"
                        )
                        step_count = cur.fetchone()["step_count"]
                        # Calculate adaptive compression using sine wave
                        # sin goes from -1 to 1, so we transform to 0 to 1
                        compression_strength = (
                            math.sin(2 * math.pi * step_count / adaptive_period) + 1
                        ) / 2

                    cur.execute(
                        """
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
                        """,
                        (version),
                    )  # , max_assistant_length))

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
                    print(
                        f"Using compression strength: {compression_strength:.3f} "
                        f"({'adaptive' if compression_strength is None else 'fixed'})"
                    )

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
                    return Program.from_row(dict(row)) if row else None
        except Exception as e:
            print(f"Error sampling parent: {e}")
            raise e

    async def update_program(self, program_id: int, updates: Dict[str, Any]) -> Program:
        """Update program with proper connection management"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Handle timing_metrics separately since it needs to be JSON serialized
                    timing_metrics = updates.pop("timing_metrics", None)
                    if timing_metrics is not None:
                        updates["timing_metrics_json"] = json.dumps(timing_metrics)

                    set_clauses = [f"{k} = %s" for k in updates.keys()]
                    values = list(updates.values())

                    cur.execute(
                        f"""
                        UPDATE programs
                        SET {", ".join(set_clauses)}
                        WHERE id = %s
                        RETURNING *
                    """,
                        values + [program_id],
                    )

                    conn.commit()
                    row = cur.fetchone()
                    return Program.from_row(
                        dict(zip([desc[0] for desc in cur.description], row))
                    )
        except Exception as e:
            print(f"Error updating program: {e}")
            raise e

    async def get_resume_state(
        self, resume_version, process_id, agent_idx=-1
    ) -> tuple[
        Optional[GameState], Optional[Conversation], Optional[int], Optional[int]
    ]:
        """Get the state to resume from"""
        try:
            # Get most recent successful program to resume from
            query = """
            SELECT * FROM programs 
            WHERE version = %s
            AND state_json IS NOT NULL
            AND value IS NOT NULL
            -- AND meta->>'process_id' = %s::text
            AND instance = %s
            ORDER BY created_at DESC
            LIMIT 1
            """

            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (resume_version, process_id, agent_idx))
                    results = cur.fetchall()
            if not results:
                print(f"No valid programs found for version {resume_version} ")
                return None, None, None, None

            # Choose a program to resume from
            program = Program.from_row(
                dict(zip([desc[0] for desc in cur.description], results[0]))
            )
            return program.state, program.conversation, program.id, program.depth

        except Exception as e:
            print(f"Error getting resume state: {e}")
            return None, None, None, None


class PostgresDBClient(DBClient):
    def __init__(
        self,
        max_conversation_length: int = 20,
        min_connections: int = 5,
        max_connections: int = 20,
        **db_config,
    ):
        super().__init__(
            max_conversation_length, min_connections, max_connections, **db_config
        )

    async def initialize(self):
        """Initialize the connection pool"""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:  # Double check pattern
                    self._pool = ThreadedConnectionPool(
                        self.min_connections, self.max_connections, **self.db_config
                    )

    def _ensure_pool(self):
        """Ensure connection pool exists with proper locking"""
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    self._pool = ThreadedConnectionPool(
                        self.min_connections, self.max_connections, **self.db_config
                    )

    @contextmanager
    def get_connection(self):
        """Regular context manager for database connections"""
        self._ensure_pool()
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                try:
                    self._pool.putconn(conn)
                except Exception as e:
                    print(f"Error returning connection to pool: {e}")
                    try:
                        self._pool.putconn(conn, close=True)
                    except:
                        pass


class SQLliteDBClient(DBClient):
    def __init__(
        self,
        max_conversation_length: int = 20,
        min_connections: int = 5,
        max_connections: int = 20,
        **db_config,
    ):
        super().__init__(
            max_conversation_length, min_connections, max_connections, **db_config
        )
        self.database_file = self.db_config.get("database_file")

    async def initialize(self):
        """Initialize the connection pool"""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:  # Double check pattern
                    self._pool = ThreadedConnectionPool(
                        self.min_connections, self.max_connections, **self.db_config
                    )

    @contextmanager
    def get_connection(self):
        """Context manager for SQLite database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.database_file)
            yield conn
        finally:
            if conn:
                conn.close()

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError)
        ),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def get_largest_version(self) -> int:
        query = """
            SELECT MAX(version)
            FROM programs
        """

        try:
            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query)
                result = cur.fetchone()
                return result[0] if result and result[0] is not None else 0
        except Exception as e:
            print(f"Error fetching largest version: {e}")
            return 0

    async def get_resume_state(
        self, resume_version, process_id, agent_idx=-1
    ) -> tuple[
        Optional[GameState], Optional[Conversation], Optional[int], Optional[int]
    ]:
        """Get the state to resume from"""
        try:
            # Get most recent successful program to resume from
            query = """
            SELECT * FROM programs 
            WHERE version = ?
            AND state_json IS NOT NULL
            AND value IS NOT NULL
            AND json_extract(meta, '$.process_id') = ?
            AND instance = ?
            ORDER BY created_at DESC
            LIMIT 1
            """

            with self.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(query, (resume_version, process_id, agent_idx))
                results = cur.fetchall()

            if not results:
                print(f"No valid programs found for version {resume_version}")
                return None, None, None, None
            resulting_program_dict = dict(
                zip([desc[0] for desc in cur.description], results[0])
            )
            # make meta, state_json achievements_json and conversation_json table a dict
            resulting_program_dict["meta"] = json.loads(resulting_program_dict["meta"])
            resulting_program_dict["achievements_json"] = json.loads(
                resulting_program_dict["achievements_json"]
            )
            resulting_program_dict["conversation_json"] = json.loads(
                resulting_program_dict["conversation_json"]
            )
            resulting_program_dict["state_json"] = json.loads(
                resulting_program_dict["state_json"]
            )
            # Choose a program to resume from
            program = Program.from_row(resulting_program_dict)
            return program.state, program.conversation, program.id, program.depth

        except Exception as e:
            print(f"Error getting resume state: {e}")
            return None, None, None, None

    @tenacity.retry(
        retry=retry_if_exception_type(
            (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError)
        ),
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
    )
    async def create_program(self, program: Program) -> Program:
        """Create a new program, now with connection management"""
        try:
            with self.get_connection() as conn:
                cur = conn.cursor()

                # Insert the program data
                cur.execute(
                    """
                    INSERT INTO programs (code, value, visits, parent_id, state_json, conversation_json, 
                                          completion_token_usage, prompt_token_usage, token_usage, response, 
                                          holdout_value, raw_reward, version, version_description, model, meta, 
                                          achievements_json, instance, depth, advantage, ticks, timing_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        program.code,
                        program.value,
                        0,  # Assuming visits is initially set to 0
                        program.parent_id,
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
                        program.depth / 2,
                        program.advantage,
                        program.ticks,
                        json.dumps(program.timing_metrics)
                        if program.timing_metrics
                        else None,
                    ),
                )

                # Get the last inserted row ID
                program.id = cur.lastrowid

                # Retrieve the created_at timestamp
                cur.execute(
                    "SELECT created_at FROM programs WHERE id = ?", (program.id,)
                )
                program.created_at = cur.fetchone()[0]
                conn.commit()
                # Return the updated program object
                return program
        except Exception as e:
            conn.rollback()
            print(f"Error creating program: {e}")
            raise e


def create_default_sqlite_db(db_file: str) -> None:
    """Create SQLite database with required schema if it doesn't exist"""
    db_path = Path(db_file)

    # Create directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create database and table if they don't exist
    conn = sqlite3.connect(db_file)
    try:
        cursor = conn.cursor()

        # Check if programs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='programs'
        """)

        if not cursor.fetchone():
            print(f"Creating SQLite database schema in {db_file}")
            cursor.execute("""
                CREATE TABLE programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    value REAL DEFAULT 0.0,
                    visits INTEGER DEFAULT 0,
                    parent_id INTEGER,
                    state_json TEXT,
                    conversation_json TEXT NOT NULL,
                    completion_token_usage INTEGER,
                    prompt_token_usage INTEGER,
                    token_usage INTEGER,
                    response TEXT,
                    holdout_value REAL,
                    raw_reward REAL,
                    version INTEGER DEFAULT 1,
                    version_description TEXT DEFAULT '',
                    model TEXT DEFAULT 'gpt-4o',
                    meta TEXT,
                    achievements_json TEXT,
                    instance INTEGER DEFAULT -1,
                    depth REAL DEFAULT 0.0,
                    advantage REAL DEFAULT 0.0,
                    ticks INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    timing_metrics_json TEXT
                )
            """)
            conn.commit()
            print("SQLite database schema created successfully!")

    finally:
        conn.close()


def create_default_postgres_db(**db_config) -> None:
    """Create PostgreSQL database with required schema if it doesn't exist"""
    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Check if programs table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'programs'
            )
        """)

        table_exists = cursor.fetchone()[0]

        if not table_exists:
            print("Creating PostgreSQL database schema")
            cursor.execute("""
                CREATE TABLE programs (
                    id SERIAL PRIMARY KEY,
                    code TEXT NOT NULL,
                    value REAL DEFAULT 0.0,
                    visits INTEGER DEFAULT 0,
                    parent_id INTEGER,
                    state_json TEXT,
                    conversation_json TEXT NOT NULL,
                    completion_token_usage INTEGER,
                    prompt_token_usage INTEGER,
                    token_usage INTEGER,
                    response TEXT,
                    holdout_value REAL,
                    raw_reward REAL,
                    version INTEGER DEFAULT 1,
                    version_description TEXT DEFAULT '',
                    model TEXT DEFAULT 'gpt-4o',
                    meta TEXT,
                    achievements_json TEXT,
                    instance INTEGER DEFAULT -1,
                    depth REAL DEFAULT 0.0,
                    advantage REAL DEFAULT 0.0,
                    ticks INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timing_metrics_json TEXT
                )
            """)
            conn.commit()
            print("PostgreSQL database schema created successfully!")

    except Exception as e:
        print(f"Error creating PostgreSQL schema: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


async def create_db_client(
    max_conversation_length: int = 40,
    min_connections: int = 2,
    max_connections: int = 5,
) -> DBClient:
    """
    Create database client based on environment configuration.
    Defaults to SQLite with automatic setup.
    """
    # Check for database type preference
    db_type = os.getenv("FLE_DB_TYPE", "sqlite").lower()

    if db_type == "postgres":
        # Use PostgreSQL if explicitly requested and configured
        required_vars = [
            "SKILLS_DB_HOST",
            "SKILLS_DB_PORT",
            "SKILLS_DB_NAME",
            "SKILLS_DB_USER",
            "SKILLS_DB_PASSWORD",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(
                f"Warning: PostgreSQL requested but missing environment variables: {missing_vars}"
            )
            print("Falling back to SQLite...")
            raise Exception(f"Missing environment variables: {missing_vars}")
        db_config = {
            "host": os.getenv("SKILLS_DB_HOST"),
            "port": os.getenv("SKILLS_DB_PORT"),
            "dbname": os.getenv("SKILLS_DB_NAME"),
            "user": os.getenv("SKILLS_DB_USER"),
            "password": os.getenv("SKILLS_DB_PASSWORD"),
        }
        create_default_postgres_db(**db_config)

        return PostgresDBClient(
            max_conversation_length=max_conversation_length,
            min_connections=min_connections,
            max_connections=max_connections,
            **db_config,
        )
    elif db_type == "sqlite":
        # Default to SQLite
        sqlite_file = os.getenv("SQLITE_DB_FILE", ".fle/data.db")
        print(f"Using SQLite database file: {sqlite_file}")

        # Auto-create SQLite database if it doesn't exist
        create_default_sqlite_db(sqlite_file)

        return SQLliteDBClient(
            max_conversation_length=max_conversation_length,
            min_connections=min_connections,
            max_connections=max_connections,
            database_file=sqlite_file,
        )
    else:
        raise Exception(f"Invalid database type: {db_type}")
