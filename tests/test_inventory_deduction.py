import pytest
from fle.env.game import FactorioInstance
from fle.env.game.game_types import Prototype
from fle.env.game.entities import Position, Direction

@pytest.fixture()
def game(instance):
    instance.initial_inventory = {
        'pipe': 10,
        'small-electric-pole': 5,
        'transport-belt': 20
    }
    instance.reset()
    yield instance.namespace
    instance.reset()

def test_inventory_deduction_after_placement(game):
    """Test that items are properly deducted from inventory after entity placement"""
    
    # Check initial inventory
    initial_inventory = game.inspect_inventory()
    initial_pipe_count = initial_inventory.get(Prototype.Pipe, 0)
    initial_pole_count = initial_inventory.get(Prototype.SmallElectricPole, 0)
    
    print(f"Initial pipes: {initial_pipe_count}")
    print(f"Initial poles: {initial_pole_count}")
    
    # Place a single pipe
    game.move_to(Position(0, 0))
    pipe = game.place_entity(Prototype.Pipe, Direction.UP, Position(0, 0))
    
    # Check inventory after placing pipe
    inventory_after_pipe = game.inspect_inventory()
    pipes_after_placement = inventory_after_pipe.get(Prototype.Pipe, 0)
    
    print(f"Pipes after placement: {pipes_after_placement}")
    
    # Assert that exactly 1 pipe was deducted
    assert pipes_after_placement == initial_pipe_count - 1, f"Expected {initial_pipe_count - 1} pipes, got {pipes_after_placement}"
    
    # Test connect_entities to see if it properly deducts items
    game.move_to(Position(5, 0))
    pole1 = game.place_entity(Prototype.SmallElectricPole, Direction.UP, Position(5, 0))
    
    game.move_to(Position(10, 0))
    pole2 = game.place_entity(Prototype.SmallElectricPole, Direction.UP, Position(10, 0))
    
    # Check inventory before connection
    inventory_before_connect = game.inspect_inventory()
    pipes_before_connect = inventory_before_connect.get(Prototype.Pipe, 0)
    
    print(f"Pipes before connection: {pipes_before_connect}")
    
    # Connect the poles with pipes
    game.connect_entities(pole1, pole2, connection_type=Prototype.Pipe)
    
    # Check inventory after connection
    inventory_after_connect = game.inspect_inventory()
    pipes_after_connect = inventory_after_connect.get(Prototype.Pipe, 0)
    
    print(f"Pipes after connection: {pipes_after_connect}")
    
    # Assert that pipes were deducted during connection
    # The exact number depends on the distance and path, but it should be less than before
    assert pipes_after_connect < pipes_before_connect, f"Expected fewer pipes after connection, before: {pipes_before_connect}, after: {pipes_after_connect}"

if __name__ == "__main__":
    pytest.main([__file__]) 