# set_entity_recipe

## Overview
The `set_entity_recipe` tool allows you to set or change the recipe of an assembling machine entity in the game. This enables automation of crafting specific items.

## Function Signature
```python
def set_entity_recipe(entity: Entity, prototype: Union[Prototype, RecipeName]) -> Entity
```

### Parameters
- `entity`: An Entity object representing the assembling machine whose recipe you want to set
- `prototype`: Either a Prototype or RecipeName enum value indicating the recipe to set

### Returns
- Returns the updated Entity with the new recipe set

## Usage Example
```python
# Place an assembling machine
assembling_machine = place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))

# Set the recipe to craft iron gear wheels
assembling_machine = set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
```

## Key Behaviors
- The tool will search for the target assembling machine within a 2-tile radius of the specified position
- If multiple machines are found, it will select the closest one
- The recipe must be supported by the assembling machine, or an error will be raised
- The tool updates the entity's recipe attribute with the new recipe name

## Error Handling
The tool will raise exceptions in the following cases:
- No assembling machine is found at the specified position
- The specified recipe is not valid for the machine
- Invalid prototype or recipe name is provided

## Requirements
- The assembling machine must exist at the specified position
- The recipe must be valid and available for the machine type
- The prototype must be a valid Prototype or RecipeName enum value

## Notes
- Always check that the recipe was successfully set by verifying the returned entity's recipe attribute
- The tool uses the Factorio game engine's recipe system, so all standard game recipe rules apply
- Recipes must be unlocked through research before they can be set

## Best Practices
1. Verify the assembling machine exists before attempting to set its recipe
2. Ensure the recipe is appropriate for the machine type
3. Handle potential errors when setting recipes
4. Update your local entity reference with the returned entity

## Related Components
- `Prototype` enum: Contains valid item and recipe definitions
- `RecipeName` enum: Contains specialized recipe names
- `Entity` class: Represents game entities including assembling machines