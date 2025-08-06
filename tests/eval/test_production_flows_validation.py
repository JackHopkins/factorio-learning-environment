import unittest
from fle.commons.models.production_flows import ProductionFlows
from fle.env.utils.achievement_calculator import AchievementTracker


class TestProductionFlowsValidation(unittest.TestCase):
    """Test production flows handle edge cases and invalid data gracefully."""

    def test_valid_production_flows(self):
        """Test normal case with valid data."""
        valid_data = {
            "input": {"iron-ore": 10.0},
            "output": {"iron-plate": 5.0},
            "crafted": [{"outputs": {"iron-plate": 5}}],
            "harvested": {"iron-ore": 10.0},
        }

        flows = ProductionFlows.from_dict(valid_data)
        self.assertEqual(flows.input["iron-ore"], 10.0)
        self.assertEqual(flows.output["iron-plate"], 5.0)
        self.assertEqual(len(flows.crafted), 1)
        self.assertEqual(flows.harvested["iron-ore"], 10.0)

    def test_missing_keys_use_defaults(self):
        """Test that missing keys get reasonable defaults."""
        minimal_data = {}

        flows = ProductionFlows.from_dict(minimal_data)
        self.assertEqual(flows.input, {})
        self.assertEqual(flows.output, {})
        self.assertEqual(flows.crafted, [])
        self.assertEqual(flows.harvested, {})
        self.assertIsNone(flows.price_list)
        self.assertIsNone(flows.static_items)

    def test_none_values_become_defaults(self):
        """Test that None values (from Lua nil) become safe defaults."""
        lua_failure_data = {
            "input": None,
            "output": None,
            "crafted": None,
            "harvested": None,
            "price_list": None,
        }

        flows = ProductionFlows.from_dict(lua_failure_data)
        self.assertEqual(flows.input, {})
        self.assertEqual(flows.output, {})
        self.assertEqual(flows.crafted, [])
        self.assertEqual(flows.harvested, {})
        self.assertIsNone(flows.price_list)

    def test_crafted_dict_converted_to_list(self):
        """Test that crafted field handles both dict and list formats."""
        # Dict format (legacy)
        dict_data = {
            "input": {},
            "output": {},
            "crafted": {
                "item1": {"outputs": {"iron-plate": 1}},
                "item2": {"outputs": {"copper-plate": 1}},
            },
            "harvested": {},
        }

        flows = ProductionFlows.from_dict(dict_data)
        self.assertIsInstance(flows.crafted, list)
        self.assertEqual(len(flows.crafted), 2)

        # List format (current)
        list_data = {
            "input": {},
            "output": {},
            "crafted": [{"outputs": {"iron-plate": 1}}],
            "harvested": {},
        }

        flows = ProductionFlows.from_dict(list_data)
        self.assertIsInstance(flows.crafted, list)
        self.assertEqual(len(flows.crafted), 1)

    def test_achievement_calculation_with_empty_data(self):
        """Test that achievement calculation handles empty production flows gracefully."""
        empty_pre = ProductionFlows.from_dict({})
        empty_post = ProductionFlows.from_dict({})

        achievements = AchievementTracker.calculate_achievements(empty_pre, empty_post)

        self.assertEqual(achievements["static"], {})
        self.assertEqual(achievements["dynamic"], {})

    def test_achievement_calculation_with_partial_data(self):
        """Test achievement calculation when some fields are missing."""
        pre_data = {
            "input": {},
            "output": {},
            "crafted": [],
            "harvested": {},
        }

        post_data = {
            "input": {"coal": 5.0},
            "output": {"iron-plate": 3.0},
            "crafted": [{"outputs": {"iron-plate": 3}}],
            "harvested": {"coal": 5.0},
        }

        pre_flows = ProductionFlows.from_dict(pre_data)
        post_flows = ProductionFlows.from_dict(post_data)

        achievements = AchievementTracker.calculate_achievements(pre_flows, post_flows)

        # Should have some static items from harvesting and crafting
        # Note: harvested items appear in static, crafted outputs appear in static
        self.assertIn("iron-plate", achievements["static"])
        self.assertEqual(achievements["static"]["iron-plate"], 3.0)

    def test_achievement_calculation_with_production_only(self):
        """Test achievement calculation with production but no harvesting/crafting."""
        pre_data = {
            "input": {},
            "output": {},
            "crafted": [],
            "harvested": {},
        }

        # Simulate pure production (e.g., from assemblers)
        post_data = {
            "input": {},
            "output": {"iron-plate": 10.0},
            "crafted": [],
            "harvested": {},
        }

        pre_flows = ProductionFlows.from_dict(pre_data)
        post_flows = ProductionFlows.from_dict(post_data)

        achievements = AchievementTracker.calculate_achievements(pre_flows, post_flows)

        # Should be pure dynamic production
        self.assertEqual(achievements["static"], {})
        self.assertIn("iron-plate", achievements["dynamic"])
        self.assertEqual(achievements["dynamic"]["iron-plate"], 10.0)

    def test_malformed_crafted_data_handled_gracefully(self):
        """Test that malformed crafted data doesn't crash the system."""
        # Missing 'outputs' key in crafted item
        malformed_data = {
            "input": {},
            "output": {"iron-plate": 1.0},
            "crafted": [{"inputs": {"iron-ore": 1}}],  # Missing 'outputs'
            "harvested": {},
        }

        pre_flows = ProductionFlows.from_dict({})
        post_flows = ProductionFlows.from_dict(malformed_data)

        # Should not crash, even with malformed crafted data
        try:
            achievements = AchievementTracker.calculate_achievements(
                pre_flows, post_flows
            )
            # Should still calculate dynamic achievements from output
            self.assertIn("iron-plate", achievements["dynamic"])
        except Exception as e:
            self.fail(
                f"Achievement calculation should handle malformed data gracefully, but raised: {e}"
            )

    def test_get_new_flows_calculation(self):
        """Test that get_new_flows correctly calculates differences."""
        pre_data = {
            "input": {"coal": 5.0},
            "output": {"iron-plate": 2.0},
            "crafted": [{"outputs": {"iron-plate": 2}}],
            "harvested": {"coal": 5.0},
        }

        post_data = {
            "input": {"coal": 10.0},
            "output": {"iron-plate": 7.0},
            "crafted": [
                {"outputs": {"iron-plate": 2}},  # Existing craft
                {"outputs": {"iron-plate": 3}},  # New craft
            ],
            "harvested": {"coal": 10.0},
        }

        pre_flows = ProductionFlows.from_dict(pre_data)
        post_flows = ProductionFlows.from_dict(post_data)

        new_flows = pre_flows.get_new_flows(post_flows)

        # Check differences are calculated correctly
        self.assertEqual(new_flows.input["coal"], 5.0)  # 10 - 5
        self.assertEqual(new_flows.output["iron-plate"], 5.0)  # 7 - 2
        self.assertEqual(new_flows.harvested["coal"], 5.0)  # 10 - 5
        self.assertEqual(len(new_flows.crafted), 1)  # One new craft item

    def test_to_dict_preserves_data(self):
        """Test that to_dict() preserves all data correctly."""
        original_data = {
            "input": {"iron-ore": 10.0},
            "output": {"iron-plate": 5.0},
            "crafted": [{"outputs": {"iron-plate": 5}}],
            "harvested": {"iron-ore": 10.0},
            "price_list": {"iron-plate": 1.0},
            "static_items": {"iron-ore": 10.0},
        }

        flows = ProductionFlows.from_dict(original_data)
        exported_data = flows.to_dict()

        self.assertEqual(exported_data["input"], original_data["input"])
        self.assertEqual(exported_data["output"], original_data["output"])
        self.assertEqual(exported_data["crafted"], original_data["crafted"])
        self.assertEqual(exported_data["harvested"], original_data["harvested"])
        self.assertEqual(exported_data["price_list"], original_data["price_list"])
        self.assertEqual(exported_data["static_items"], original_data["static_items"])


if __name__ == "__main__":
    unittest.main()
