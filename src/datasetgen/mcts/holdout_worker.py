from datetime import datetime

from datasetgen.mcts.evaluation_task import EvaluationTask
from datasetgen.mcts.evaluation_worker import EvaluatorWorker
from datasetgen.mcts.program import Program
from datasetgen.mcts.task_status import TaskStatus


class HoldoutWorker(EvaluatorWorker):
    async def _process_task(self, task: EvaluationTask):
        program = await self.db.get_program(task.program_id)

        # Run do-nothing program to measure passive gains
        baseline_program = Program(
            code="await asyncio.sleep(5)",  # Passive waiting
            conversation=program.conversation
        )
        baseline_reward = await self.instance.eval(baseline_program.code)

        # Run actual program
        reward, state, response = await self.instance.eval(program.code)

        # Compute relative advantage
        relative_reward = reward - baseline_reward

        await self.db.update_program(program.id, {
            'value': relative_reward,
            'state': state.dict(),
            'baseline_reward': baseline_reward,
            'raw_reward': reward
        })

        await self.db.update_task(task.id, {
            'status': TaskStatus.COMPLETED,
            'completed_at': datetime.now(),
            'result': {
                'reward': relative_reward,
                'baseline': baseline_reward,
                'raw_reward': reward,
                'response': response
            }
        })