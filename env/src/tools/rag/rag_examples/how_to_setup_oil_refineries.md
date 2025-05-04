## Oil Refinery

### Placing a oil refinery

Example:
Placing a oil refinery near a existing pumpjack at Position(x=-50, y=0)
Also connect the oil refinery to a steam engine, that will power the refinery. To power the oil refinery, it needs to be connected to a power source via electric poles
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

The outputs of oil refineries can be extracted by pipes and connected to storage tanks or chemical plants
