import unittest
from unittest.mock import MagicMock, patch
from collections import Counter
from datetime import datetime

import numpy as np

from fle.commons.models.program import Program
from fle.eval.algorithms.mcts import KLDiversityAchievementSampler


def program_row(program_id, achievements):
    """Return the complete row selected by Program.from_row."""
    return {
        "id": program_id,
        "code": "pass",
        "conversation_json": {"messages": []},
        "value": 0.0,
        "visits": 0,
        "parent_id": None,
        "state_json": None,
        "raw_reward": None,
        "holdout_value": None,
        "created_at": datetime.now(),
        "prompt_token_usage": None,
        "completion_token_usage": None,
        "token_usage": None,
        "response": None,
        "version": 1,
        "version_description": "",
        "meta": {},
        "achievements_json": achievements,
        "instance": -1,
        "depth": 0,
        "advantage": 0.0,
        "ticks": 0,
        "timing_metrics_json": [],
    }


class TestKLDiversityAchievementSampler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db_client = MagicMock()
        self.sampler = KLDiversityAchievementSampler(
            db_client=self.db_client, window_size=3, temperature=1.0
        )

    def test_compute_achievement_frequencies(self):
        # Test with numeric values
        achievements = {
            "static": {"stone": 5, "iron-ore": 9},
            "dynamic": {"iron-plate": 1},
        }
        frequencies = self.sampler._compute_achievement_frequencies(achievements)

        self.assertEqual(frequencies["static-stone"], 5)
        self.assertEqual(frequencies["static-iron-ore"], 9)
        self.assertEqual(frequencies["dynamic-iron-plate"], 1)

        # Test with empty achievements
        frequencies = self.sampler._compute_achievement_frequencies({})
        self.assertEqual(len(frequencies), 0)

    def test_compute_kl_divergence(self):
        # Create two simple distributions
        p = Counter({"stone": 5, "stone-furnace": 1})
        q = Counter({"stone": 5, "stone-furnace": 3})

        kld = self.sampler._compute_kl_divergence(p, q)

        # KL divergence should be non-negative
        self.assertGreater(kld, 0)

        # KL divergence should be zero for identical distributions
        kld_same = self.sampler._compute_kl_divergence(p, p)
        self.assertAlmostEqual(kld_same, 0, places=5)

        # Test with disjoint achievements
        p = Counter({"depth": 5})
        q = Counter({"branches": 3})
        kld = self.sampler._compute_kl_divergence(p, q)
        self.assertIsInstance(kld, float)
        self.assertFalse(np.isnan(kld))

    @patch("numpy.random.choice")
    async def test_sample_parent(self, mock_choice):
        # Mock database results
        mock_results = [
            {
                "id": 1,
                "achievements_json": {
                    "static": {"stone": 5, "iron-ore": 9},
                    "dynamic": {"iron-plate": 1},
                },
                "version": 1,
                "conversation_json": {"messages": []},
            },
            {
                "id": 2,
                "achievements_json": {
                    "static": {"stone": 7, "iron-ore": 9},
                    "dynamic": {"iron-plate": 2},
                },
                "version": 1,
                "conversation_json": {"messages": []},
            },
            {
                "id": 3,
                "achievements_json": {
                    "static": {
                        "stone": 5,
                    },
                    "dynamic": {},
                },
                "version": 1,
                "conversation_json": {"messages": []},
            },
        ]

        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_results
        mock_cursor.fetchone.return_value = program_row(
            1, mock_results[0]["achievements_json"]
        )
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        self.db_client.get_connection.return_value.__enter__.return_value = mock_conn

        # Mock numpy's random choice to return a specific ID
        mock_choice.return_value = 1

        # Test sampling
        program = await self.sampler.sample_parent(version=1)

        self.assertIsInstance(program, Program)
        self.assertEqual(program.id, 1)

        # Verify database queries were called correctly
        query, params = mock_cursor.execute.call_args_list[0].args
        self.assertEqual(
            " ".join(query.split()),
            "SELECT id, achievements_json FROM programs WHERE version = %s "
            "AND achievements_json IS NOT NULL ORDER BY created_at DESC LIMIT %s",
        )
        self.assertEqual(params, (1, 3))

    async def test_sample_parent_no_results(self):
        # Mock empty database results
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        self.db_client.get_connection.return_value.__enter__.return_value = mock_conn

        # Test sampling with no results
        program = await self.sampler.sample_parent(version=1)
        self.assertIsNone(program)

    async def test_sample_parent_single_result(self):
        # Mock single database result
        mock_result = {
            "id": 1,
            "achievements_json": {
                "static": {"stone": 5, "iron-ore": 9},
                "dynamic": {"iron-plate": 1},
            },
            "version": 1,
            "conversation_json": {"messages": []},
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [mock_result]
        mock_cursor.fetchone.return_value = program_row(
            1, mock_result["achievements_json"]
        )
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        self.db_client.get_connection.return_value.__enter__.return_value = mock_conn

        # Test sampling with single result
        program = await self.sampler.sample_parent(version=1)

        self.assertIsInstance(program, Program)
        self.assertEqual(program.id, 1)


if __name__ == "__main__":
    unittest.main()
