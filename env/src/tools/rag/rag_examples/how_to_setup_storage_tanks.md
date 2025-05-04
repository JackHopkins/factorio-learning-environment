## Storage tanks

You can use storage tanks to store liquids

### Placing a storage tank to store liquid

Example:
Place a storage tank and store petroleum gas from an existing oil refinery
```python
# get the oil_refinery
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))

# create a buildingboxwith with 4 tile buffer for the oilrefinery
building_box = BuildingBox(width = Prototype.StorageTank.WIDTH + 4, height = Prototype.StorageTank.HEIGHT + 4)

# put down the storagetank atleast 5 spaces away from oilrefinery
ref_pos = Position(x = oil_refinery.position.x+10, y = oil_refinery.position.y+10)
coords = nearest_buildable(Prototype.StorageTank,building_box, ref_pos)
# place the storage tank at the centre coordinate
# first move to the center coordinate
move_to(coords.center)
storage_tank = place_entity(Prototype.StorageTank, position = coords.center, direction = Direction.LEFT)

# Get the petroleum-gas output point of oil refinery
output_petroleum_gas_connection_points = [x for x in oil_refinery.output_connection_points if x.type == "petroleum-gas"]
assert len(output_petroleum_gas_connection_point) > 0, f"No petroleum gas output points in oil refinery"
output_petroleum_gas_connection_point = output_petroleum_gas_connection_points[0]

# connect the storagetank and oil refinery
pipes = connect_entities(output_petroleum_gas_connection_point, storage_tank, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the oil_refinery at {oil_refinery.position} to a storage tank at {storage_tank.position} to store petroleum gas with {pipes}")
```


### Using an existing storage tank with liquid
If a storage tank has liquid, the liquid can be sent to other fluid processors like oil refinery and chemical plant via pipes

Example:
Connect an existing storage tank with petroleum gas to a existing chemical plant
```python
# get the chemical_plant and storage_tank
chemical_plant = get_entity(Prototype.ChemicalPlant, position = Position(x = -25, y = 10))
storage_tank = get_entity(Prototype.StorageTank, position = Position(x = -20, y = 10))

# Get the petroleum-gas input point of chemical plant
input_petroleum_gas_connection_points = [x for x in oil_refinery.input_connection_points if x.type == "petroleum-gas"]
assert len(input_petroleum_gas_connection_points) > 0, f"No petroleum gas input points in chemical_plant"
input_petroleum_gas_connection_point = input_petroleum_gas_connection_points[0]

# connect the storagetank and chemical_plant
pipes = connect_entities(storage_tank, input_petroleum_gas_connection_points, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the storage_tank at {storage_tank.position} to a chemical_plant at {chemical_plant.position} to process petroleum gas with {pipes}")
```