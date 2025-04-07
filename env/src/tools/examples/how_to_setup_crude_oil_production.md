## Pumpjacks

To harvest crude oil from the environment, it needs to be done with pumpjacks
Crude oil can be processed to petroleum gas
### Placing a pumpjack

Example:
Placing a pumpjack near a crude oil patch
Also connect the pumpjack to a steam engine, that will power the pumpjack. To power the pumpjack, it needs to be connected to a power source via electric poles
NB: TO CHECK HOW TO SET UP ELECTRICITY NETWORKS, QUERY "HOW TO SET UP ELECTRICITY?"
```python
# Get the crude oil resource patch
resource_pos = nearest(Resource.CrudeOil)
# Define area for pumpjack
pump_box = BuildingBox(height=Prototype.PumpJack.HEIGHT, width=Prototype.PumpJack.WIDTH)

# Find buildable area
buildable_area = nearest_buildable(
    Prototype.PumpJack,
    pump_box,
    resource_pos
)

# Place pumpjack
move_to(buildable_area.center)
pumpjack = place_entity(
    Prototype.PumpJack,
    position=buildable_area.center
)
# log your actions
print(f"Placed pumpjack to harvest crude oil at {pumpjack.position}")

# power the pumpjack by connecting to an existing steam engine
steam_engine = get_entity(Prototype.SteamEngine, position=Position(x=0, y=0))
# Connect power to pumpjack
poles = connect_entities(steam_engine,
                     pumpjack,
                     Prototype.SmallElectricPole)
print(f"Powered pumpjack at {pumpjack.position} with {poles}")
# wait for 5 seconds to check power
sleep(5)
pumpjack = get_entity(Prototype.PumpJack, pumpjackefinery.position)
assert pumpjack.energy > 0, f"pumpjack at {pumpjack.position} is not receiving power"
print(f"Pumpjack at {pumpjack.position} has been successfully powered")
```

### Putting down a storage tank for pumpjack output crude oil
The outputs of pumpjacks can be stored in storage tanks or directly connected to oil refineries

Example:
Connect a pumpjack to a existing oil_refinery to process crude oil
```python
# get the oil_refinery and pumpjack
oil_refinery = get_entity(Prototype.OilRefinery, position = Position(x = -25, y = 10))
pumpjack = get_entity(Prototype.PUMPJACK, position = Position(x = -20, y = 10))

# connect the pumpjack and oil refinery
pipes = connect_entities(pumpjack, oil_refinery, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the pumpajck at {pumpjack.position} to a oil refinery at {oil_refinery.position} to process crude oil with {pipes}")
```