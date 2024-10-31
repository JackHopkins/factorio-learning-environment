from factorio_instance import *

"""
Main Objective: We require one Radar. The final success should be checked by looking if a Radar is in inventory
"""



"""
Step 1: Gather resources
- Mine coal for fuel
- Mine iron ore (at least 25 units)
- Mine copper ore (at least 8 units)
- Mine stone (at least 5 units for an additional furnace)
OUTPUT CHECK: Verify that we have the required amounts of coal, iron ore, copper ore, and stone in our inventory
"""
# Inventory at the start of step {}
#Step Execution

# Define the resources we need to gather
resources_to_gather = [
    (Resource.Coal, 10),
    (Resource.IronOre, 25),
    (Resource.CopperOre, 8),
    (Resource.Stone, 5)
]

# Function to get the resource name regardless of its type
def get_resource_name(resource):
    if isinstance(resource, tuple):
        return resource[0]
    elif isinstance(resource, Enum):
        return resource.name
    else:
        return str(resource)

# Gather resources
for resource_type, required_amount in resources_to_gather:
    resource_name = get_resource_name(resource_type)
    current_inventory_count = inspect_inventory().get(resource_name, 0)
    
    while current_inventory_count < required_amount:
        resource_position = nearest(resource_type)
        move_to(resource_position)
        amount_to_harvest = min(required_amount - current_inventory_count, 5)  # Harvest in batches of 5
        harvested = harvest_resource(resource_position, amount_to_harvest)
        
        current_inventory_count = inspect_inventory().get(resource_name, 0)
        print(f"Harvested {harvested} {resource_name}. Current count: {current_inventory_count}")

    assert current_inventory_count >= required_amount, f"Failed to gather enough {resource_name}. Required: {required_amount}, Current: {current_inventory_count}"

# Final inventory check
final_inventory = inspect_inventory()
print("Final inventory after gathering resources:")
for resource_type, required_amount in resources_to_gather:
    resource_name = get_resource_name(resource_type)
    assert final_inventory.get(resource_name, 0) >= required_amount, f"Not enough {resource_name} in final inventory"
    print(f"{resource_name}: {final_inventory.get(resource_name, 0)}")

print("All required resources gathered successfully!")


"""
Step 2: Craft and set up furnaces
- Craft a stone furnace using 5 stone
- Place the new furnace next to the existing one
- Fuel both furnaces with coal
OUTPUT CHECK: Confirm that both furnaces are placed and fueled
"""
# Inventory at the start of step {'coal': 10, 'stone': 5, 'iron-ore': 25, 'copper-ore': 8}
#Step Execution

# Step 2: Craft and set up furnaces

# Craft a stone furnace
craft_item(Prototype.StoneFurnace, 1)
print("Crafted a stone furnace.")

# Get position of existing stone furnace
existing_furnace_position = nearest(Prototype.StoneFurnace)

# Move near to where we want to place the new furnace
move_to(existing_furnace_position)

# Place new stone furnace next to existing one
new_furnace = place_entity_next_to(
    Prototype.StoneFurnace,
    reference_position=existing_furnace_position,
    direction=Direction.RIGHT,
    spacing=0
)
print(f"Placed new stone furnace at {new_furnace.position}")

# Fueling process for both furnaces

# Inspect current inventory for coal count
coal_count = inspect_inventory().get('coal', 0)
print(f"Coal available in inventory: {coal_count}")

assert coal_count >= 2, "Not enough coal in inventory to fuel both furnaces."

# Distribute coal between two furnaces equally (assuming equal distribution is fine here)
coal_per_furnace = min(coal_count // 2, 5) # Ensure not more than needed per each

# Fuel existing stone furnace first
existing_stone_furnace_entities = get_entities({Prototype.StoneFurnace})
existing_stone_furnace = [f for f in existing_stone_furnace_entities if f.position.is_close(existing_furnace_position)][0]
insert_item(Prototype.Coal, target=existing_stone_furnace, quantity=coal_per_furnace)
print(f"Fueled existing stone furnace with {coal_per_furnace} units of coal.")

# Fuel newly placed stone furnace 
insert_item(Prototype.Coal, target=new_furnace, quantity=coal_per_furnace)
print(f"Fueled new stone furnace with {coal_per_furnace} units of coal.")

print("Both furnaces are placed and fueled successfully!")


"""
Step 3: Smelt plates
- Smelt 25 iron plates using iron ore
- Smelt 8 copper plates using copper ore
OUTPUT CHECK: Verify that we have 25 iron plates and 8 copper plates in our inventory
"""
# Placeholder 3

"""
Step 4: Craft intermediate components
- Craft 10 copper cables using 5 copper plates
- Craft 5 electronic circuits using 15 copper cables and 5 iron plates
- Craft 5 iron gear wheels using 10 iron plates
OUTPUT CHECK: Confirm that we have 5 electronic circuits and 5 iron gear wheels in our inventory
"""
# Placeholder 4

"""
Step 5: Craft Radar
- Craft 1 Radar using 5 electronic circuits, 5 iron gear wheels, and 10 iron plates
OUTPUT CHECK: Verify that we have 1 Radar in our inventory

##
"""
# Placeholder 5