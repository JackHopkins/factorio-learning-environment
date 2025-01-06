import unittest
from unittest.mock import Mock, patch
from collections import Counter

import numpy as np
from psycopg2.extras import DictRow
from torch.utils.data import WeightedRandomSampler

from search.mcts.samplers.dynamic_reward_weighted_sampler import DynamicRewardWeightedSampler
from search.model.program import Program
from search.mcts.samplers.kld_achievement_sampler import KLDiversityAchievementSampler


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


if __name__ == '__main__':
    unittest.main()