from factorio_instance import *
def test_craft_and_place_transport_belts():
    # Check if 5 transport belts have been crafted and placed
    placed_belts = inspect_entities(radius=20)
    transport_belts = [entity for entity in placed_belts if entity['name'] == 'transport-belt']
    
    if len(transport_belts) < 5:
        print(f"Objective not complete. Only {len(transport_belts)} transport belts placed. Need 5.")
        return False
    
    # Check if the belts are placed in a line or curve (adjacent to each other)
    connected_belts = 1
    for i in range(len(transport_belts) - 1):
        current_belt = transport_belts[i]
        next_belt = transport_belts[i + 1]
        
        # Check if belts are adjacent (Manhattan distance of 1)
        if (abs(current_belt['position']['x'] - next_belt['position']['x']) + 
            abs(current_belt['position']['y'] - next_belt['position']['y'])) == 1:
            connected_belts += 1
    
    if connected_belts < 5:
        print(f"Objective not complete. Only {connected_belts} transport belts are connected. Need 5.")
        return False
    
    # Check if player's inventory has any unused transport belts
    player_inventory = inspect_inventory()
    unused_belts = player_inventory.get(Prototype.TransportBelt.value[0], 0)
    
    if unused_belts > 0:
        print(f"Objective not complete. {unused_belts} transport belts remain in inventory. Place all 5.")
        return False
    
    print("Objective complete! 5 transport belts have been crafted and placed correctly.")
    return True
