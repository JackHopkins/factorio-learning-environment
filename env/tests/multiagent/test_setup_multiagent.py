import pytest
from time import sleep

from instance import FactorioInstance
from game_types import Prototype
from cluster.local.setup_multiagent import setup_multiagent
from cluster.local.cluster_ips import get_local_container_ips

@pytest.fixture
def multi_instance(instance):
    """Creates a second FactorioInstance with a different player_index"""
    # First instance is already created by the base fixture
    instance1 = instance
    instance1.num_players = 2
    
    # Create second instance with different player index
    ips, udp_ports, tcp_ports = get_local_container_ips()
    instance2 = FactorioInstance(
        address='localhost',
        bounding_box=200,
        tcp_port=tcp_ports[-1],
        cache_scripts=False,
        fast=True,
        player_index=2,  # Different player index
        num_players=2,
        inventory={
            'iron-plate': 50,
            'copper-plate': 50,
        }
    )
    
    yield instance1, instance2
    
    # Cleanup
    instance2.reset()

def test_multiagent_interaction(multi_instance):
    """Test interaction between multiple agents in the same server"""
    instance1, instance2 = multi_instance
    
    # Initially, trying to use instance2 should fail because second player isn't set up
    with pytest.raises(Exception) as exc_info:
        instance2.namespace.craft_item(Prototype.IronChest, quantity=1)
    assert "player not found" in str(exc_info.value).lower()
    
    # Set up additional players using setup_multiagent
    setup_multiagent(
        num_clients=2,  # We want 2 additional players (3 total)
        server_address="localhost:34197",
        factorio_binary_path="/Applications/factorio.app/Contents/MacOS/factorio",
        timeout=60
    )
    
    # Give server time to register new players
    sleep(2)
    
    # Verify 3 players exist using RCON command
    response = instance1.connection.send_command('/players')
    assert 'client0' in response
    assert 'client1' in response
    
    # Now both instances should be able to interact with the server
    # Test with instance1
    initial_iron_plate1 = instance1.namespace.inspect_inventory()[Prototype.IronPlate]
    instance1.namespace.craft_item(Prototype.IronChest, quantity=1)
    final_iron_plate1 = instance1.namespace.inspect_inventory()[Prototype.IronPlate]
    assert initial_iron_plate1 - final_iron_plate1 == 8  # Iron chest costs 8 plates
    
    # Test with instance2
    initial_iron_plate2 = instance2.namespace.inspect_inventory()[Prototype.IronPlate]
    instance2.namespace.craft_item(Prototype.IronChest, quantity=1)
    final_iron_plate2 = instance2.namespace.inspect_inventory()[Prototype.IronPlate]
    assert initial_iron_plate2 - final_iron_plate2 == 8
    
    # Test environment updates
    # Have instance1 place a chest
    pos1 = instance1.namespace.player_location
    chest1 = instance1.namespace.place_entity(Prototype.IronChest, position=pos1)
    
    # instance2 should be able to see the chest
    entities = instance2.namespace.get_entities(Prototype.IronChest)
    assert any(e.position == pos1 for e in entities)
    
    # Have instance2 place a chest nearby
    pos2 = instance2.namespace.player_location
    chest2 = instance2.namespace.place_entity(Prototype.IronChest, position=pos2)
    
    # instance1 should be able to see both chests
    entities = instance1.namespace.get_entities(Prototype.IronChest)
    assert len(entities) == 2
    assert any(e.position == pos1 for e in entities)
    assert any(e.position == pos2 for e in entities)
