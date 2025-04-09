## Oil Refinery

### Placing a oil refinery

Example:
Set recipe for oil refinery to get petroleum gas
```python
# get the pumpjack
pumpjack = get_entity(Prototype.PumpJack, position=Position(x=-50, y=0))
oil_refinery = get_entity(Prototype.Oilrefinery, position = Position(x = -25, y = 10))

# Set the recipe to basc oil processing
# IMPORTANT: The recipe for chemical plants and oil refineries must be set before connecting to inputs and outputs
oil_refinery = set_entity_recipe(oil_refinery, RecipeName.BasicOilProcessing)
print(f"Set the recipe of oil refinery at {oil_refinery.position} to BasicOilProcessing")

# connect with underground and overground pipes to the pumpjack
pipes = connect_entities(pumpjack, oil_refinery, connection_type={Prototype.UndergroundPipe, Prototype.Pipe})
print(f"Connected the pumpjack at {pumpjack.position} to oil refinery at {oil_refinery.position} with {pipes}")
```