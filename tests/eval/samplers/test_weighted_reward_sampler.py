import unittest
from unittest.mock import Mock

from fle.eval.algorithms.mcts.samplers import DynamicRewardWeightedSampler


class TestWeightedRewardSampler(unittest.TestCase):
    def setUp(self):
        self.db_client = Mock()
        self.sampler = DynamicRewardWeightedSampler(
            db_client=self.db_client,
            max_conversation_length=5,
            maximum_lookback=2,
        )

    async def test_sample_parent_with_lookback(self):
        depths = []
        # Test sampling with single result
        for _ in range(100):
            program = await self.sampler.sample_parent(version=312)
            depths.append(program.depth)

        max_depth = max(depths)
        min_depth = min(depths)

        print(max_depth, min_depth)
        self.assertEqual(True, False)
        self.assertEqual(max_depth, 26)
        self.assertEqual(min_depth, 24)


if __name__ == "__main__":
    unittest.main()
