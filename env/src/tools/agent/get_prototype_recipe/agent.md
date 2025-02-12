# get_prototype_recipe Tool Guide

The `get_prototype_recipe` tool retrieves the complete recipe information for any craftable item, fluid or entity in Factorio. This tool is essential for understanding crafting requirements and planning production chains.

## Core Functionality

The tool returns a Recipe object containing:
- List of required ingredients with quantities
- List of products produced
- Additional metadata like crafting time and category

## Basic Usage

```python
# Get recipe for any prototype
# for example, iron gear wheels
recipe = get_prototype_recipe(Prototype.IronGearWheel)

# Access recipe information
for ingredient in recipe.ingredients:
    print(f"Need {ingredient.count} {ingredient.name}")
```

### Parameters

The tool accepts one of:
1. `Prototype` enum value
2. `RecipeName` enum value
3. Raw string name of the recipe

### Return Value

Returns a `Recipe` object with the following structure:
```python
Recipe(
    name=str,
    ingredients=[Ingredient(name=str, count=int, type=str)],
    products=[Product(name=str, count=int, probability=float, type=str)]
)
```

## Common Use Cases

### 1. Basic Recipe Checking
```python
# Check iron gear wheel requirements
recipe = get_prototype_recipe(Prototype.IronGearWheel)
print("Recipe for Iron Gear Wheel:")
for ingredient in recipe.ingredients:
    print(f"Need: {ingredient.count} {ingredient.name}")
```

## Best Practices

1. **Always Check Recipe Before Crafting**
```python
# Print recipe before attempting to craft
def print_recipe_requirements(prototype):
    recipe = get_prototype_recipe(prototype)
    print(f"Requirements for {recipe.name}:")
    for ingredient in recipe.ingredients:
        print(f"- {ingredient.count}x {ingredient.name}")
```

## Example Recipes

Here are some common recipe examples:

### Basic Items
```python
# Advanced Circuit
recipe = get_prototype_recipe(Prototype.AdvancedCircuit)
# Requires: Electronic Circuits, Copper Cable, Plastic

# Processing Unit
recipe = get_prototype_recipe(Prototype.ProcessingUnit)
# Requires: Advanced Circuits, Electronic Circuits, Sulfuric Acid

# Sulfuric acid
recipe = get_prototype_recipe(RecipeName.SulfuricAcid)
# Requires: Iron Plates, SUlfur, Water
```