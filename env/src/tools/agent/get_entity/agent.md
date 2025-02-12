# get_entity

The `get_entity` tool allows you to get objects and update variables with their new versions. It is crucial to regularly get the newest variables at the start of every program to ensure no variables are stale

Inputs
- Prototype.X
- Position

Outputs
Entity object

## Basic Usage
Creating power connection
Assume the SolarPanel and ElectronicMiningDrill exist at the given positions
```python
# get the variables
solar_panel = get_entity(Prototype.SolarPanel, Position(x = 1, y = 2))
drill_1 = get_entity(Prototype.ElectricMiningDrill, Position(x = 10, y = 28))
# create the main connection
main_power_connection = connect_entities(solar_panel, 
                                    drill_1,
                                    Prototype.SmallElectricPole)
```

Connecting one inserter to another (inserter_1 at Position(x = 12, y = 11) to inserter_2 at Position(x = 0, y = 0))
```python
# get the inserter entities
inserter_1 = get_entity(Prototype.BurnerInserter, position = Position(x = 12, y = 11))
inserter_2 = get_entity(Prototype.BurnerInserter, position = Position(x = 0, y = 0))
# connect the two inserters (source -> target). Passing in the entity will result in them being connected intelligently.
belts = connect_entities(
    inserter_1, #.drop_position,
    inserter_2, #.pickup_position,
    Prototype.TransportBelt
)
```

**Outdated variables**
   - Regularly update your variables using entity = get_entity(Prototype.X, entity.position)

