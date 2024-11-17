import json
from typing import Optional, Dict, Any

import psycopg2
import tenacity
from tenacity import wait_exponential, retry_if_exception_type

from datasetgen.mcts.evaluation_task import EvaluationTask
from datasetgen.mcts.program import Program


class DBClient:
    def __init__(self, **db_config):
        self.conn = psycopg2.connect(**db_config)

    async def create_program(self, program: Program) -> Program:
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO programs (code, value, visits, parent_id, state_json, conversation_json, completion_token_usage, prompt_token_usage, token_usage, response, holdout_value, raw_reward, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """, (program.code, program.value, program.visits, program.parent_id,
                  program.state.to_raw() if program.state else None,
                  json.dumps(program.conversation.dict()),
                  program.completion_token_usage,
                  program.prompt_token_usage,
                  program.token_usage,
                  program.response,
                  program.holdout_value,
                  program.raw_reward,
                  program.version
                  ))

            id, created_at = cur.fetchone()
            self.conn.commit()
            program.id = id
            program.created_at = created_at
            return program

    @tenacity.retry(retry=retry_if_exception_type((psycopg2.OperationalError, psycopg2.InterfaceError)), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def sample_parent(self, version=1) -> Optional[Program]:
        with self.conn.cursor() as cur:
            # Get sampled ID
            cur.execute(f"SELECT sample_parent({version})")
            sampled_id = cur.fetchone()[0]
            if not sampled_id:
                return None

            # Fetch full program data
            cur.execute("SELECT * FROM programs WHERE id = %s", (sampled_id,))
            row = cur.fetchone()
            return Program.from_row(dict(zip([desc[0] for desc in cur.description], row)))


    async def update_program(self, program_id: int, updates: Dict[str, Any]) -> Program:
        with self.conn.cursor() as cur:
            set_clauses = [f"{k} = %s" for k in updates.keys()]
            values = list(updates.values())

            cur.execute(f"""
                UPDATE programs
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING *
            """, values + [program_id])

            self.conn.commit()
            row = cur.fetchone()
            return Program.from_row(dict(zip([desc[0] for desc in cur.description], row)))

    async def update_task(self, task_id: int, updates: Dict[str, Any]) -> EvaluationTask:
        with self.conn.cursor() as cur:
            set_clauses = [f"{k} = %s" for k in updates.keys()]
            values = list(updates.values())

            cur.execute(f"""
                UPDATE evaluation_queue
                SET {', '.join(set_clauses)}
                WHERE id = %s
                RETURNING *
            """, values + [task_id])

            self.conn.commit()
            return EvaluationTask.parse_obj(cur.fetchone())