## Best Practices

1. **Inventory Verification**
Example - Safe smelting ore into plates
```python
# move to the position to place the entity
move_to(position)
furnace = place_entity(Prototype.StoneFurnace, position=position)
print(f"Placed the furnace to smelt plates at {furnace.position}")

# we also update the furnace variable by returning it from the function
# This ensures it doesnt get stale and the inventory updates are represented in the variable
furnace = insert_item(Prototype.Coal, furnace, quantity=5)  # Don't forget fuel
furnace = insert_item(Prototype.IronOre, furnace, quantity=10)

# 3. Wait for smelting (with safety timeout)
for _ in range(30):  # Maximum 30 seconds wait
    if inspect_inventory(furnace)[Prototype.IronPlate] >= 10:
        break
    sleep(1)
else:
    raise Exception("Smelting timeout - check fuel and inputs")

# final check for the inventory of furnace
iron_plates_in_furnace = inspect_inventory(furnace)[Prototype.IronPlate]
assert iron_plates_in_furnace>=10, "Not enough iron plates in furnace"
print(f"Smelted 10 iron plates")
   ```