import unittest
from unittest.mock import MagicMock, Mock, patch

from fle.commons.models.program import Program
from fle.eval.algorithms.mcts.samplers import DynamicRewardWeightedSampler


class TestWeightedRewardSampler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_client = MagicMock()
        self.sampler = DynamicRewardWeightedSampler(
            db_client=self.db_client,
            max_conversation_length=5,
            maximum_lookback=2,
        )

    async def test_sample_parent_with_lookback(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor
        self.db_client.get_connection.return_value.__enter__.return_value = connection
        cursor.fetchone.side_effect = [
            {"step_count": 0},
            {"max": 26},
            {"id": 2},
        ]
        cursor.fetchall.return_value = [
            {"id": 1, "advantage": -1.0},
            {"id": 2, "advantage": 1.0},
        ]
        selected = Mock(depth=25)

        with (
            patch.object(Program, "from_row", return_value=selected),
            patch(
                "fle.eval.algorithms.mcts.samplers.dynamic_reward_weighted_sampler.random.choices",
                return_value=[2],
            ) as choose,
        ):
            program = await self.sampler.sample_parent(version=312)

        self.assertEqual(program.depth, 25)
        cursor.execute.assert_any_call(unittest.mock.ANY, (312, 24))
        cursor.execute.assert_any_call(unittest.mock.ANY, (2,))
        candidate_ids = choose.call_args.args[0]
        weights = choose.call_args.kwargs["weights"]
        self.assertEqual(candidate_ids, [1, 2])
        self.assertAlmostEqual(sum(weights), 1.0)
        self.assertGreater(weights[1], weights[0])


if __name__ == "__main__":
    unittest.main()
