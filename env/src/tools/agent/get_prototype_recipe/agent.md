# get_prototype_recipe Tool Guide

The `get_prototype_recipe` tool retrieves the complete recipe information for any craftable item or entity in Factorio. This tool is essential for understanding crafting requirements and planning production chains.

## Core Functionality

The tool returns a Recipe object containing:
- List of required ingredients with quantities
- List of products produced
- Additional metadata like crafting time and category

## Basic Usage

```python
# Get recipe for any prototype
recipe = get_prototype_recipe(Prototype.X)

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

### 2. Production Chain Planning
```python
def get_total_raw_materials(prototype, quantity=1):
    recipe = get_prototype_recipe(prototype)
    total_materials = {}
    
    for ingredient in recipe.ingredients:
        total_materials[ingredient.name] = ingredient.count * quantity
        
    return total_materials

# Example usage
materials = get_total_raw_materials(Prototype.ElectronicCircuit, 10)
```

### 3. Verifying Crafting Requirements
```python
def can_craft_item(prototype):
    recipe = get_prototype_recipe(prototype)
    inventory = inspect_inventory()
    
    for ingredient in recipe.ingredients:
        if inventory[ingredient.name] < ingredient.count:
            return False
    return True
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

2. **Handle Complex Recipes**
```python
def analyze_recipe_complexity(prototype):
    recipe = get_prototype_recipe(prototype)
    return {
        "ingredient_count": len(recipe.ingredients),
        "products": [p.name for p in recipe.products],
        "total_ingredients": sum(i.count for i in recipe.ingredients)
    }
```

3. **Resource Planning**
```python
def calculate_batch_requirements(prototype, batch_size):
    recipe = get_prototype_recipe(prototype)
    requirements = {}
    
    for ingredient in recipe.ingredients:
        requirements[ingredient.name] = ingredient.count * batch_size
        
    return requirements
```

## Common Patterns

### Production Line Setup
```python
def setup_production_line(prototype):
    recipe = get_prototype_recipe(prototype)
    
    # Calculate required machines
    total_ingredients = len(recipe.ingredients)
    inserters_needed = total_ingredients + len(recipe.products)
    
    print(f"Production line for {recipe.name} requires:")
    print(f"- {inserters_needed} inserters")
    print(f"- {total_ingredients} input chests")
    print(f"- {len(recipe.products)} output chests")
```

### Recipe Chain Analysis
```python
def analyze_production_chain(final_product):
    def _get_ingredients(proto):
        recipe = get_prototype_recipe(proto)
        return [ing.name for ing in recipe.ingredients]
    
    chain = {final_product: _get_ingredients(final_product)}
    return chain
```

## Error Handling

```python
try:
    recipe = get_prototype_recipe(prototype)
except Exception as e:
    print(f"Error getting recipe: {e}")
    # Handle invalid recipe case
```

## Tips for Effective Usage

1. **Recipe Verification**
   - Always check recipe exists before crafting
   - Verify ingredient counts
   - Check for fluid ingredients

2. **Production Planning**
   - Calculate total requirements upfront
   - Consider crafting times
   - Account for product probabilities

3. **Resource Management**
   - Track raw material requirements
   - Calculate intermediate products
   - Consider production ratios

## Common Mistakes to Avoid

1. **Forgetting to Check Recipe**
   - Always verify recipe exists
   - Check all ingredients are available
   - Verify crafting category

2. **Ignoring Product Quantities**
   - Some recipes produce multiple items
   - Products may have probabilities
   - Consider byproducts

3. **Resource Calculation Errors**
   - Account for all ingredient quantities
   - Consider crafting efficiency
   - Include intermediate products

## Debugging Tips

If recipe retrieval fails:

1. **Check Prototype Name**
   - Verify prototype exists
   - Check for typos
   - Ensure recipe is unlocked

2. **Verify Recipe Access**
   - Check technology requirements
   - Verify game state
   - Check for mod dependencies

3. **Handle Special Cases**
   - Check for fluid ingredients
   - Verify crafting category
   - Consider recipe variations

## Example Recipes

Here are some common recipe examples:

### Basic Items
```python
# Iron Gear Wheel
recipe = get_prototype_recipe(Prototype.IronGearWheel)
# Requires: 2 Iron Plates

# Electronic Circuit
recipe = get_prototype_recipe(Prototype.ElectronicCircuit)
# Requires: 1 Iron Plate, 3 Copper Cable
```

### Advanced Items
```python
# Advanced Circuit
recipe = get_prototype_recipe(Prototype.AdvancedCircuit)
# Requires: Electronic Circuits, Copper Cable, Plastic

# Processing Unit
recipe = get_prototype_recipe(Prototype.ProcessingUnit)
# Requires: Advanced Circuits, Electronic Circuits, Sulfuric Acid
```