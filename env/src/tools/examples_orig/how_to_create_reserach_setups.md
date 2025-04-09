### 4. Research Systems

#### Basic Research Setup
```python
def build_research_facility(power_source, lab):
    # Connect power
    poles = connect_entities(power_source,
                         lab,
                         Prototype.SmallElectricPole)
    print(f"Powered lab at {lab.position} with {poles}")
    # Add science pack inserter
    # put it to the left of lab
    inserter = place_entity_next_to(Prototype.BurnerInserter,
                                        lab.position,
                                        direction=Direction.LEFT,
                                        spacing=0)
    # rotate it to input items into the lab                                          
    inserter = rotate_entity(inserter, Direction.RIGHT)
    # Place input chest
    chest = place_entity(Prototype.WoodenChest,
                                     inserter.pickup_position,
                                     direction=Direction.LEFT)
    print(f"Placed chest at {chest.position} to input automation packs to lab at {lab.position}")
    
    return lab, inserter, chest
```