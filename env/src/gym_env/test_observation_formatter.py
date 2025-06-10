import unittest
from gym_env.observation_formatter import BasicObservationFormatter

class TestObservationFormatter(unittest.TestCase):
    def test_entity_grouping(self):
        formatter = BasicObservationFormatter()
        
        # Test case with multiple entities of different types
        test_entities = [
            "name='burner-mining-drill', direction=DOWN, position=(16.0, 71.0), type='mining-drill'",
            "name='burner-mining-drill', direction=DOWN, position=(19.0, 71.0), type='mining-drill'",
            "name='wooden-chest', direction=UP, position=(16.5, 72.5), type='container'",
            "name='wooden-chest', direction=UP, position=(19.5, 72.5), type='container'"
        ]
        
        result = formatter.format_entities(test_entities)
        
        # Verify that entities are grouped by type
        self.assertIn("mining-drill: 2", result)
        self.assertIn("container: 2", result)
        
        # Verify that position is not used for grouping
        self.assertNotIn("71.0", result)
        self.assertNotIn("72.5", result)

if __name__ == '__main__':
    unittest.main() 