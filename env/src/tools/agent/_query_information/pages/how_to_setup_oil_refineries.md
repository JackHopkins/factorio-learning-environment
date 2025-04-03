## Oil Refinery

### Placing a oil refinery

Example:
Placing a oil refinery near a existing pumpjack at Position(x=-50, y=0)
Also connect the oil refinery to a steam engine, that will power the refinery. To power the oil refinery, it needs to be connected to a power source via electric poles
NB: TO CHECK HOW TO SET UP ELECTRICITY NETWORKS, PRINT OUT THE "how_to_create_electricity_generators" WIKI PAGE
NB: TO CHECK HOW TO SET UP PUMPJACKS, PRINT OUT THE "how_to_setup_crude_oil_production" WIKI PAGE
```python
# get the pumpjack
pumpjack = get_entity(Prototype.PumpJack, position=Position(x=-50, y=0))

# create a buildingboxwith with 4 tile buffer for the oilrefinery
building_box = BuildingBox(width = Prototype.OilRefinery.WIDTH + 4, height = Prototype.OilRefinery.HEIGHT + 4)

# put down the oilrefinery atleast 10 spaces away from pumpjack
ref_pos = Position(x = pumpjack.position.x+10, y = pumpjack.position.y+10)
coords = nearest_buildable(Prototype.OilRefinery,building_box, ref_pos)
# place the oil refinery at the centre coordinate
# first move to the center coordinate
move_to(coords.center)
oil_refinery = place_entity(Prototype.OilRefinery, position = coords.center, direction = Direction.LEFT)

# power the oil refinery by connecting to an existing steam engine
steam_engine = get_entity(Prototype.SteamEngine, position=Position(x=0, y=0))
# Connect power to oil refinery
poles = connect_entities(steam_engine,
                     oil_refinery,
                     Prototype.SmallElectricPole)
print(f"Powered oil refinery at {oil_refinery.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
oil_refinery = get_entity(Prototype.OilRefinery, oil_refinery.position)
assert oil_refinery.energy > 0, f"oil_refinery at {oil_refinery.position} is not receiving power"
print(f"Oil Refinery at {oil_refinery.position} has been successfully powered")
```

### Setting recipes for oil refineries
Before rotating or using the oilrefinery, the recipe must be set

Available recipes for oil refinery

RecipeName.BasicOilProcessing = "basic-oil-processing" # Recipe for producing petroleum gas with a oil refinery
RecipeName.AdvancedOilProcessing = "advanced-oil-processing" # Recipe for producing petroleum gas, heavy oil and light oil with a oil refinery
RecipeName.CoalLiquefaction = "coal-liquefaction" # Recipe for producing petroleum gas in a oil refinery

Example:
Set recipe for a existing oil refinery to get petroleum gas
Also connect a existing pumpjack to the oil refinery
```python
# get the pumpjack and oil refineries
pumpjack = get_entity(Prototype.PumpJack, position=Position(x=-50, y=0))
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))

# Set the recipe to basc oil processing
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
oil_refinery = set_entity_recipe(oil_refinery, RecipeName.BasicOilProcessing)
print(f"Set the recipe of oil refinery at {oil_refinery.position} to BasicOilProcessing")

# connect with underground and overground pipes to the pumpjack
pipes = connect_entities(pumpjack, oil_refinery, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the pumpjack at {pumpjack.position} to oil refinery at {oil_refinery.position} with {pipes}")
```

### Connecting the oil refinery outputs

The outputs of oil refineries can be extracted by pipes

Example:
Connect a oil refinery to a existing storage tank to store petroleum gas
NB: TO CHECK HOW TO SET UP STORAGE TANKS, PRINT OUT THE "how_to_setup_storage_tanks" WIKI PAGE
```python
# get the oil_refinery and storage tank
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))
storage_tank = get_entity(Prototype.StorageTank, position = Position(x = -20, y = 10))

# Get the petroleum-gas output point of oil refinery
output_petroleum_gas_connection_points = [x for x in oil_refinery.output_connection_points if x.type == "petroleum-gas"]
assert len(output_petroleum_gas_connection_point) > 0, f"No petroleum gas output points in oil refinery"
output_petroleum_gas_connection_point = output_petroleum_gas_connection_points[0]

# connect the storagetank and oil refinery
pipes = connect_entities(output_petroleum_gas_connection_point, storage_tank, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the oil refinery at {oil_refinery.position} to a storage tank at {storage_tank.position} to store petroleum gas with {pipes}")
```

Example:
Connect a oil refinery to a existing chemical plant to process petroleum gas
```python
# get the oil_refinery and chemical plant
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))
chemical_plant = get_entity(Prototype.ChemicalPlant, position = Position(x = -20, y = 10))

# Get the petroleum-gas output point of oil refinery
output_petroleum_gas_connection_points = [x for x in oil_refinery.output_connection_points if x.type == "petroleum-gas"]
assert len(output_petroleum_gas_connection_point) > 0, f"No petroleum gas output points in oil refinery"
output_petroleum_gas_connection_point = output_petroleum_gas_connection_points[0]

# connect the chemical_plant and oil refinery
pipes = connect_entities(output_petroleum_gas_connection_point, chemical_plant, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the oil refinery at {oil_refinery.position} to a chemical_plant at {chemical_plant.position} to process petroleum gas with {pipes}")
```

