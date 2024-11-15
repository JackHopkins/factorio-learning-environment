import asyncio
from datetime import datetime
from typing import Optional

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.evaluation_task import EvaluationTask
from datasetgen.mcts.task_status import TaskStatus
from factorio_instance import FactorioInstance


class EvaluatorWorker:
    def __init__(self, instance_id: int, db_client: DBClient, instance: FactorioInstance):
        self.instance_id = instance_id
        self.db = db_client
        self.instance = instance

    async def run(self):
        while True:
            if task := await self._claim_task():
                await self._process_task(task)
            else:
                await asyncio.sleep(1)

    async def _claim_task(self) -> Optional[EvaluationTask]:
        with self.db.conn.cursor() as cur:
            cur.execute("""
                UPDATE evaluation_queue
                SET status = %s, instance_id = %s, started_at = NOW()
                WHERE id = (
                    SELECT id FROM evaluation_queue 
                    WHERE status = %s
                    ORDER BY id ASC LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, program_id
            """, (TaskStatus.RUNNING, self.instance_id, TaskStatus.PENDING))
            return EvaluationTask.parse_obj(cur.fetchone()) if cur.rowcount else None

    async def _process_task(self, task: EvaluationTask):
        program = await self.db.get_program(task.program_id)
        reward, state, response = await self.instance.eval(program.code)

        await self.db.update_program(program.id, {
            'value': reward,
            'state': state.dict()
        })

        await self.db.update_task(task.id, {
            'status': TaskStatus.COMPLETED,
            'completed_at': datetime.now(),
            'result': {'reward': reward, 'response': response}
        })