# craft_item

The craft tool allows you to create items and entities in Factorio by crafting them from their component materials. This document explains how to use the tool effectively and covers important considerations.

## Basic Usage

To craft an item, use the `craft_item` function with a Prototype and optional quantity:

```python
# Craft a single iron chest
game.craft_item(Prototype.IronChest)

# Craft multiple items
game.craft_item(Prototype.CopperCable, quantity=20)
```

## Key Features

### Automatic Resource Management
- The tool automatically checks if you have the required resources in your inventory
- It handles resource consumption and inventory updates
- For items requiring intermediate resources, it will attempt to craft those first

### Recursive Crafting
The tool supports recursive crafting of intermediate components. For example:
- If you try to craft an electronic circuit but lack copper cable
- The tool will first attempt to craft the required copper cable
- Then proceed with crafting the electronic circuit

### Technology Requirements
- Some items require specific technologies to be researched before they can be crafted
- The tool will check technology prerequisites and notify you if research is needed
- You cannot craft items that require unresearched technologies

## Important Considerations

### Raw Resources
- Raw resources like iron ore and copper ore cannot be crafted
- These must be mined using mining tools instead
- Attempting to craft raw resources will result in an error

### Resource Requirements
Before crafting, ensure:
1. You have sufficient raw materials in your inventory
2. Required technologies are researched
3. The item is craftable by hand (some items require machines)

### Error Handling
The tool provides detailed error messages for common issues:
- Insufficient resources
- Missing technology requirements
- Uncraftable items
- Recursive crafting loops

## Examples

### Basic Crafting
```python
# Craft 5 iron chests (requires 8 iron plates each)
game.craft_item(Prototype.IronChest, quantity=5)

# Craft 20 copper cables (requires 10 copper plates)
game.craft_item(Prototype.CopperCable, quantity=20)
```

### Complex Crafting
```python
# Craft electronic circuits (requires copper cables and iron plates)
game.craft_item(Prototype.ElectronicCircuit, quantity=4)
```

### Error Cases
```python
# Will fail - raw resource
try:
    game.craft_item(Prototype.IronOre)
except Exception as e:
    print(e)  # "Cannot craft iron-ore - it is a raw resource"

# Will fail - insufficient resources
try:
    game.craft_item(Prototype.IronChest, quantity=100)
except Exception as e:
    print(e)  # Details about missing resources
```

## Best Practices

1. **Resource Verification**
   - Check inventory before attempting large crafts
   - Ensure you have extra resources for intermediate components

2. **Error Handling**
   - Always wrap crafting operations in try-except blocks
   - Handle potential failures gracefully
   - Check error messages for specific issues

3. **Efficient Crafting**
   - Craft intermediate components in bulk when needed repeatedly
   - Consider crafting order to minimize resource waste
   - Be aware of technology requirements before attempting crafts

## Common Errors and Solutions

### "Recipe is not unlocked yet"
- **Cause**: Required technology hasn't been researched
- **Solution**: Research the necessary technology first

### "Cannot be crafted"
- **Cause**: Item requires a machine (e.g., furnace or assembling machine)
- **Solution**: Use appropriate manufacturing facility instead of hand crafting

### "Missing ingredients"
- **Cause**: Insufficient resources in inventory
- **Solution**: Gather or craft required resources first

### "Recursive crafting loop detected"
- **Cause**: Circular dependency in crafting requirements
- **Solution**: Break the loop by crafting intermediate components first

## Limitations

1. Cannot craft items that require:
   - Specific machines (e.g., smelting recipes)
   - Unresearched technologies
   - Special crafting categories

2. Cannot craft raw resources (must be mined)

3. Limited by inventory space

## Integration with Other Tools

The craft tool works well with:
- `inspect_inventory` - Check resource availability
- `harvest_resource` - Gather raw materials
- Research tools - Unlock new crafting recipes