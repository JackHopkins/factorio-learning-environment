# inspect_inventory

The `inspect_inventory` tool allows you to check the contents of your own inventory or any entity's inventory (chests, furnaces, assembling machines, etc). This guide explains how to use it effectively.

## Basic Usage

```python
inspect_inventory(entity: Optional[Union[Entity, Position]] = None) -> Inventory
```

The function returns an Inventory object that can be queried using Prototype objects.

### Parameters

- `entity`: Optional Entity or Position to inspect (if None, inspects player inventory)

### Return Value

Returns an Inventory object that can be accessed in two ways:
```python
inventory = inspect_inventory()
# Using [] syntax
coal_count = inventory[Prototype.Coal]  # Returns 0 if not present

# Using get() method
coal_count = inventory.get(Prototype.Coal, 0)  # Second argument is default value
```

## Common Usage Patterns

1. **Check Player Inventory**
```python
# Check your own inventory
inventory = inspect_inventory()
coal_count = inventory[Prototype.Coal]
iron_plates = inventory[Prototype.IronPlate]
```

2. **Check Entity Inventory**
```python
# Check chest contents
chest = place_entity(Prototype.IronChest, position=pos)
chest_inventory = inspect_inventory(entity=chest)
# Returns combined inventory of all items
items_in_chest = chest_inventory[Prototype.IronPlate]
```

3. **Check Furnace Contents**
```python
# Inspect furnace for both input and output items
furnace = place_entity(Prototype.StoneFurnace, position=pos)
furnace_inventory = inspect_inventory(entity=furnace)
# Returns combined inventory of:
# - Input slot (ores/raw materials)
# - Output slot (plates/products)
ore_count = furnace_inventory[Prototype.IronOre]
plate_count = furnace_inventory[Prototype.IronPlate]
```

4. **Check Assembling Machine**
```python
# Check both input and output inventories
machine = place_entity(Prototype.AssemblingMachine1, position=pos)
machine_inventory = inspect_inventory(entity=machine)
# Returns combined inventory of:
# - Input inventory (ingredients)
# - Output inventory (products)
input_count = machine_inventory[Prototype.IronPlate]
output_count = machine_inventory[Prototype.IronGearWheel]
```

## Best Practices

1. **Always Check Before Operations**
```python
# Check inventory before crafting
inventory = inspect_inventory()
if inventory[Prototype.IronPlate] >= 5:
    craft_item(Prototype.IronGearWheel)
```

### 2. Labs
```python
lab = place_entity(Prototype.Lab, position=pos)
lab_inventory = inspect_inventory(entity=lab)
# Returns science pack inventory
```

## Common Patterns

1. **Fuel Monitoring Pattern**
To monitor fuel for burner types, you need to use the .fuel attribute of burner types
```python
def check_furnace_fuel_levels(furnace: Entity) -> bool:
    """Monitor furnace fuel levels"""
    has_fuel = furnace.fuel[Prototype.Coal] > 0
    return has_fuel 
```