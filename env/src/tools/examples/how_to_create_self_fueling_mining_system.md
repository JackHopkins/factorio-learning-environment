## Self fueling system

```python
# Define building area
coal_patch_position = nearest(Resource.Coal)
building_box = BuildingBox(width=Prototype.BurnerMiningDrill.WIDTH, height=Prototype.BurnerMiningDrill.HEIGHT + Prototype.BurnerInserter.HEIGHT + Prototype.TransportBelt.HEIGHT)  #  drill width, drill + inserter + belt height
buildable_coords = nearest_buildable(Prototype.BurnerMiningDrill, building_box, coal_patch_position)

# Place drill
move_to(buildable_coords.center)
drill = place_entity(Prototype.BurnerMiningDrill, 
                        position=buildable_coords.center,
                        direction=Direction.DOWN)
print(f"Placed BurnerMiningDrill to mine coal at {drill.position}")

# Place self-fueling inserter
inserter = place_entity_next_to(Prototype.BurnerInserter,
                                    drill.position,
                                    direction=Direction.DOWN,
                                    spacing=0)
inserter = rotate_entity(inserter, Direction.UP)
print(f"Placed inserter at {inserter.position} to fuel the drill")

# Connect with belts
belts = connect_entities(drill.drop_position,
                            inserter.pickup_position,
                            Prototype.TransportBelt)
print(f"Connected drill to inserter with transport belt")

# Bootstrap system
drill = insert_item(Prototype.Coal, drill, quantity=5)
```