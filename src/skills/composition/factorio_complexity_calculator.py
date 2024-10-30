import ast
import os
from typing import Dict
from composition_utils import load_schema


class FactorioComplexityCalculator:

    ENTITY_OPERATIONS = load_schema("../../controllers")

    @staticmethod
    def calculate_complexity(implementation: str) -> int:
        """Calculate implementation complexity based on:
        - Number of distinct entity operations/interactions
        - Nesting depth of control structures
        - Number of assertions (validation complexity)
        - Resource management operations
        """
        try:
            # Clean the implementation string
            implementation = implementation.strip()
            tree = ast.parse(implementation)

            class ComplexityVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.complexity = 0
                    self.depth = 0
                    self.entity_operations = set()

                def visit_Call(self, node):
                    # Count Factorio-specific operations
                    if isinstance(node.func, ast.Name):
                        op_name = node.func.id
                        if op_name in FactorioComplexityCalculator.ENTITY_OPERATIONS:
                            self.entity_operations.add(op_name)
                            # Entity operations are more complex
                            self.complexity += 2
                    self.generic_visit(node)

                def visit_Assert(self, node):
                    # Each assertion represents a validation point
                    self.complexity += 1
                    self.generic_visit(node)

                def visit_If(self, node):
                    # Control flow adds complexity
                    self.depth += 1
                    self.complexity += self.depth
                    self.generic_visit(node)
                    self.depth -= 1

                def visit_While(self, node):
                    # Loops are more complex than simple conditionals
                    self.depth += 1
                    self.complexity += self.depth * 2
                    self.generic_visit(node)
                    self.depth -= 1

                def get_final_complexity(self):
                    # Base complexity from control structures and assertions
                    base = self.complexity

                    # Add complexity for unique entity operations
                    operations = len(self.entity_operations)

                    # Calculate final score:
                    # - Base complexity from control flow and assertions
                    # - Number of unique entity operations (weighted higher)
                    # - Additional complexity for each operation type
                    return base + (operations * 3)

            visitor = ComplexityVisitor()
            visitor.visit(tree)
            return visitor.get_final_complexity()

        except Exception as e:
            print(f"Failed to calculate complexity: {str(e)}")
            return 0

    @staticmethod
    def calculate_score(implementation: str,
                        starting_inventory: Dict[str, int],
                        inventory_difference: Dict[str, int]) -> int:
        """Calculate implementation score based on:
        - Resource efficiency (using minimum required resources)
        - Implementation robustness (assertions and validations)
        - Solution determinism (prefer predictable solutions)
        """
        score = 100  # Start with base score

        try:
            tree = ast.parse(implementation)

            # Reward proper validation
            asserts = len([node for node in ast.walk(tree) if isinstance(node, ast.Assert)])
            score += min(asserts * 5, 50)  # Cap assertion bonus

            # Calculate resource efficiency
            resources_used = sum(abs(v) for v in inventory_difference.values() if v < 0)
            resources_available = sum(v for v in starting_inventory.values())
            if resources_available > 0:
                efficiency = 1 - (resources_used / resources_available)
                score += int(efficiency * 50)

            # Analyze implementation patterns
            class ScoreVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.deductions = 0
                    self.bonuses = 0

                def visit_While(self, node):
                    # Slight deduction for loops (prefer deterministic solutions)
                    self.deductions += 5
                    self.generic_visit(node)

                def visit_Call(self, node):
                    # Count Factorio operations
                    if isinstance(node.func, ast.Name):
                        if node.func.id in FactorioComplexityCalculator.ENTITY_OPERATIONS:
                            # Small bonus for each successful entity operation
                            self.bonuses += 1

                def visit_Assert(self, node):
                    # Bonus for entity state validation
                    if isinstance(node.test, ast.Compare):
                        if any('direction' in ast.unparse(node) or
                               'position' in ast.unparse(node) or
                               'entities' in ast.unparse(node)):
                            self.bonuses += 2

            visitor = ScoreVisitor()
            visitor.visit(tree)

            # Apply bonuses and deductions
            score = max(0, score + visitor.bonuses - visitor.deductions)
            return min(score, 1000)  # Cap at 1000

        except Exception as e:
            print(f"Failed to calculate score: {str(e)}")
            return 0


if __name__ == '__main__':
    # Test implementation from example
    implementation = '''
# Find iron ore patch and move there
iron_pos = nearest(Resource.IronOre)
move_to(iron_pos)

# Place burner mining drill on iron patch
drill = place_entity(Prototype.BurnerMiningDrill, Direction.RIGHT, iron_pos)
assert drill is not None, "Failed to place burner mining drill"
insert_item(Prototype.Coal, drill, 5)

# Place initial belt at drill output
belt = place_entity(Prototype.TransportBelt, Direction.RIGHT, drill.drop_position)
assert belt is not None, "Failed to place transport belt"

# Place furnace with spacing for inserter
furnace = place_entity_next_to(Prototype.StoneFurnace, belt.position, Direction.UP, spacing=1)
assert furnace is not None, "Failed to place stone furnace"
insert_item(Prototype.Coal, furnace, 5)

# Place input inserter between belt and furnace
insert1 = place_entity_next_to(Prototype.BurnerInserter, furnace.position, Direction.DOWN, spacing=0)
insert1 = rotate_entity(insert1, Direction.UP)
assert insert1 is not None, "Failed to place input inserter"
assert insert1.direction == Direction.UP
insert_item(Prototype.Coal, insert1, 5)

# Place chest for output
chest = place_entity_next_to(Prototype.IronChest, furnace.position, Direction.RIGHT, spacing=1)
assert chest is not None, "Failed to place iron chest"

# Place output inserter between furnace and chest
insert2 = place_entity_next_to(Prototype.BurnerInserter, chest.position, Direction.LEFT, spacing=0)
insert2 = rotate_entity(insert2, Direction.RIGHT)
assert insert2 is not None, "Failed to place output inserter"
assert insert2.direction == Direction.RIGHT
insert_item(Prototype.Coal, insert2, 5)

# Verify setup
inspection = inspect_entities(drill.position, radius=10)
assert len([e for e in inspection.entities if e.name == "burner-mining-drill"]) == 1
'''

    calculator = FactorioComplexityCalculator()

    # Test complexity calculation
    complexity = calculator.calculate_complexity(implementation)
    print(f"Complexity: {complexity}")
