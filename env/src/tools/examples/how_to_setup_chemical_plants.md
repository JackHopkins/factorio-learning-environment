## Chemical plants

### Placing a chemical plant near a oil refinery

Example:
Placing a chemical plant near a existing oil_refinery at Position(x=-50, y=0)
Also connect the chemical plant to a steam engine, that will power the engine. To power the chemical plant, it needs to be connected to a power source via electric poles
NB: TO CHECK HOW TO SET UP ELECTRICITY NETWORKS, PRINT OUT THE "how_to_create_electricity_generators" WIKI PAGE
```python
# get the oil_refinery
oil_refinery = get_entity(Prototype.OilRefinery, position=Position(x=-50, y=0))

# create a buildingboxwith with 4 tile buffer for the ChemicalPlant
building_box = BuildingBox(width = Prototype.ChemicalPlant.WIDTH + 4, height = Prototype.ChemicalPlant.HEIGHT + 4)

# put down the ChemicalPlant atleast 10 spaces away from oil_refinery
ref_pos = Position(x = oil_refinery.position.x+10, y = oil_refinery.position.y+10)
coords = nearest_buildable(Prototype.ChemicalPlant,building_box, ref_pos)
# place the chemical_plant at the centre coordinate
# first move to the center coordinate
move_to(coords.center)
chemical_plant = place_entity(Prototype.ChemicalPlant, position = coords.center, direction = Direction.LEFT)

# power the chemical_plant by connecting to an existing steam engine
steam_engine = get_entity(Prototype.SteamEngine, position=Position(x=0, y=0))
# Connect power to chemical_plant
poles = connect_entities(steam_engine,
                     chemical_plant,
                     Prototype.SmallElectricPole)
print(f"Powered oil refinery at {chemical_plant.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
chemical_plant = get_entity(Prototype.ChemicalPlant, chemical_plant.position)
assert chemical_plant.energy > 0, f"chemical_plant at {chemical_plant.position} is not receiving power"
print(f"Chemical plant at {chemical_plant.position} has been successfully powered")
```

### Setting recipes for chemical plants
Before rotating or using the chemical plants, the recipe must be set

Available recipes for chemical plants

Liquid outputs
These need to be either stored in a storagetank or sent to other liquidprocessors. Transporting must be via pipes
RecipeName.HeavyOilCracking = "heavy-oil-cracking" # Recipe for producing light oil in a chemical plant. This is a liquid and therefore the output must be extracted via pipes respective output_connection_points
RecipeName.LightOilCracking = "light-oil-cracking" # Recipe for producing petroleum gas in a chemical plant. This is a liquid and therefore the output must be extracted via pipes respective output_connection_points
Prototype.SulfuricAcid # Recipe for producing SulfuricAcid in a chemical plant. This is a liquid and therefore the output must be extracted via pipes respective output_connection_points
Prototype.Lubricant # Recipe for producing lubricant in a chemical plant. This is a liquid and therefore the output must be extracted via pipes respective output_connection_points

Solid outputs
These need to be extracted frm the chemical plant via inserters into either chests or transport belts transporting them to other structures 
RecipeName.SolidFuelFromHeavyOil = "solid-fuel-from-heavy-oil" # Recipe for producing solid fuel in a chemical plant from heavy oil. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant
RecipeName.SolidFuelFromLightOil = "solid-fuel-from-light-oil" # Recipe for producing solid fuel in a chemical plant from light oil. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant
RecipeName.SolidFuelFromPetroleumGas = "solid-fuel-from-petroleum-gas" # Recipe for producing solid fuel in a chemical plant from petroleum gas. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant
Prototype.PlasticBar # Recipe for producing plastic bars in a chemical plant. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant
Prototype.Sulfur # Recipe for producing Sulfuric in a chemical plant. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant
Prototype.Battery # Recipe for producing batteries in a chemical plant. This is a solid output and therefore the output must be extracted inserters that take items away from the chemical plant

Example:
Set recipe for a existing chemical plant to get sulfuric acid
Also connect a existing oil refinery to the chemical plant
```python
# get the chemical plant and oil refineries
chemical_plant = get_entity(Prototype.ChemicalPlant, position=Position(x=-50, y=0))
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))

# Set the recipe to Lubricant
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
chemical_plant = set_entity_recipe(chemical_plant, Prototype.Lubricant)
print(f"Set the recipe of chemical plant at {chemical_plant.position} to Lubricant")

# connect with underground and overground pipes to the oil refinery
pipes = connect_entities(oil_refinery, chemical_plant, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the chemical_plant at {chemical_plant.position} to oil refinery at {oil_refinery.position} with {pipes}")
```

### Storing liquid outputs of chemical plants 
The liquid outputs of chemical plants can be stored in storage tanks via pipes