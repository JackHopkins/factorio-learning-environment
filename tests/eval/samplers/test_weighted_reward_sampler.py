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
            {"id": 1},
        ]
        cursor.fetchall.return_value = [{"id": 1, "advantage": 1.0}]
        selected = Mock(depth=26)

        with patch.object(Program, "from_row", return_value=selected):
            program = await self.sampler.sample_parent(version=312)

        self.assertEqual(program.depth, 26)
        cursor.execute.assert_any_call(unittest.mock.ANY, (312, 24))


if __name__ == "__main__":
    unittest.main()
