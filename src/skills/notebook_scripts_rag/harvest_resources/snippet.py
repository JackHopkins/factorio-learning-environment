
# get the resources required
ore_required = [(Resource.IronOre, 25), (Resource.Stone, 5), (Resource.Coal, 10), (Resource.CopperOre, 7)]

# loop through the resources required
for resource, amount in ore_required:
    # get the nearest resource
    resource_position = nearest(resource)
    # move to the resource
    move_to(resource_position)
    # harvest the resource
    harvest_resource(resource_position, amount)
    # check if we have enough resources
    resource_count = inspect_inventory()[resource]
    assert resource_count >= amount, f"Failed to mine enough {resource}. Expected {amount}, but got {resource_count}"
    print(f"Mined {resource_count} {resource}")
    print(f"Current inventory: {inspect_inventory()}")

final_inventory = inspect_inventory()
print(f"Final inventory after harvesting: {final_inventory}")