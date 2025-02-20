# set_entity_recipe

## Overview
The `set_entity_recipe` tool allows you to set or change the recipe of an assembling machine, chemical plant or oil refinery entity in the game. This enables automation of crafting specific items.

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
Set recipe for assembling machine
```python
# get the assembling machine
assembling_machine = get_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))

# Set the recipe to craft iron gear wheels
assembling_machine = set_entity_recipe(assembling_machine, Prototype.IronGearWheel)
```
## Usage Example
Set recipe for chemical plant
Chemical plants can use both RecipeName recipes and Prototype recipes
```python
# get the chemical plant
chemical_plant = get_entity(Prototype.ChemicalPlant, position=Position(x=0, y=0))

# Set the recipe to craft solid fuel from heavy oil
chemical_plant = set_entity_recipe(chemical_plant, RecipeName.SolidFuelFromHeavyOil)
print(f"Set the recipe of chemical plant at {chemical_plant.position} to SolidFuelFromHeavyOil")

chemical_plant = set_entity_recipe(chemical_plant, Prototype.Sulfur)
print(f"Set the recipe of chemical plant at {chemical_plant.position} to Sulfur")
```



## Key Behaviors
- The tool will search for the target entity within a 2-tile radius of the specified position
- If multiple machines are found, it will select the closest one
- The recipe must be supported by the target entity, or an error will be raised
- The tool updates the entity's recipe attribute with the new recipe name

## Error Handling
The tool will raise exceptions in the following cases:
- No target entity is found at the specified position
- The specified recipe is not valid for the machine
- Invalid prototype or recipe name is provided

## Notes
- The tool uses the Factorio game engine's recipe system, so all standard game recipe rules apply
- Recipes must be unlocked through research before they can be set