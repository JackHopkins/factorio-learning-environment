# craft_item

The craft tool allows you to create items and entities in Factorio by crafting them from their component materials. This document explains how to use the tool effectively and covers important considerations.

## Basic Usage

To craft an item, use the `craft_item` function with a Prototype and optional quantity:

```python
# Craft a single iron chest
craft_item(Prototype.IronChest)

# Craft multiple items
craft_item(Prototype.CopperCable, quantity=20)
```
## Key Features

### Automatic Resource Management
- The tool automatically checks if you have the required resources in your inventory
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

- Raw resources like iron ore and copper ore cannot be crafted. These must be mined using mining tools instead. Attempting to craft raw resources will result in an error.
- Crafting if your inventory is full will also result in an error.


## Examples

### Basic Crafting
```python
# Craft 5 iron chests (requires 8 iron plates each)
craft_item(Prototype.IronChest, quantity=5)

# Craft 20 copper cables (requires 10 copper plates)
craft_item(Prototype.CopperCable, quantity=20)
```