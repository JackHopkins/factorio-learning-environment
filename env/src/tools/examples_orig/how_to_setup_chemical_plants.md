## Chemical plants

### Placing a chemical plant near a oil refinery

Example:
Set recipe for chemical plant and connect to input and output storage tanks
```python
# get the chemical plant
chemical_plant = get_entity(Prototype.ChemicalPlant, position=Position(x=0, y=0))

# Set the recipe to craft solid fuel from heavy oil
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
chemical_plant = set_entity_recipe(chemical_plant, RecipeName.HeavyOilCracking)
print(f"Set the recipe of chemical plant at {chemical_plant.position} to HeavyOilCracking")

# get the input storage tank
storage_tank = get_entity(Prototype.StorageTank, position=Position(x=10, y=0))
# connect with underground and overground pipes
# the order matters as the storage tank will be connected to recipe inputs
pipes = connect_entities(storage_tank, chemical_plant, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the input tank at {storage_tank.position} to chemical plant at {chemical_plant.position} with {pipes}")

# get the output storage tank
output_storage_tank = get_entity(Prototype.StorageTank, position=Position(x=-10, y=0))
# connect with underground and overground pipes
# the order matters as the storage tank will be connected to recipe outputs
pipes = connect_entities(chemical_plant, output_storage_tank, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the output tank at {output_storage_tank.position} to chemical plant at {chemical_plant.position} with {pipes}")

```