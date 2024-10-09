# Helper function to place entities near the player
def place_near_player(prototype, offset_x, offset_y):
    player_pos = Position(x=0, y=0)
    for dx in range(5):  # Try different x offsets
        for dy in range(5):  # Try different y offsets
            entity = place_entity(prototype, position=Position(x=player_pos.x + offset_x + dx, y=player_pos.y + offset_y + dy))
            if entity:
                return entity
    assert False, f"Failed to place {prototype.value[0]}"

# 1. Set up basic resource gathering
iron_drill = place_near_player(Prototype.BurnerMiningDrill, 1, 1)
coal_chest = place_near_player(Prototype.WoodenChest, 3, 1)
stone_furnace = place_near_player(Prototype.StoneFurnace, 5, 1)

# 2. Create a steam power unit
offshore_pump = place_near_player(Prototype.OffshorePump, 1, 3)
boiler = place_near_player(Prototype.Boiler, 3, 3)
steam_engine = place_near_player(Prototype.SteamEngine, 5, 3)
electric_pole = place_near_player(Prototype.SmallElectricPole, 7, 3)

# Connect water pump to boiler and boiler to steam engine
connect_entities(offshore_pump, boiler, Prototype.Pipe)
connect_entities(boiler, steam_engine, Prototype.Pipe)

# 3. Set up copper plate production
copper_drill = place_near_player(Prototype.BurnerMiningDrill, 1, 5)
copper_furnace = place_near_player(Prototype.StoneFurnace, 5, 5)

# 4. Create an iron gear wheel production line
gear_assembler = place_near_player(Prototype.AssemblingMachine1, 1, 7)
set_entity_recipe(gear_assembler, Prototype.IronGearWheel)
assert gear_assembler.recipe and gear_assembler.recipe.name == "iron-gear-wheel", "Failed to set iron gear wheel recipe"

# 5. Set up firearm magazine production
magazine_assembler = place_near_player(Prototype.AssemblingMachine1, 5, 7)
set_entity_recipe(magazine_assembler, Prototype.FirearmMagazine)
assert magazine_assembler.recipe and magazine_assembler.recipe.name == "firearm-magazine", "Failed to set firearm magazine recipe"

# 6. Create a small logistics network
connect_entities(stone_furnace, magazine_assembler, Prototype.TransportBelt)
connect_entities(copper_furnace, magazine_assembler, Prototype.TransportBelt)
connect_entities(gear_assembler, magazine_assembler, Prototype.TransportBelt)

# 7. Set up storage
storage_chest = place_near_player(Prototype.IronChest, 7, 7)
inserter = place_near_player(Prototype.BurnerInserter, 6, 7)

# 8. Supply coal to burner entities
for entity in [iron_drill, copper_drill, stone_furnace, copper_furnace, boiler, inserter]:
    insert_item(Prototype.Coal, entity, 5)

# 9. Verify production line
sleep(60)  # Wait for production to start

inspection = inspect_entities(position=magazine_assembler.position, radius=20)
assert any(entity.name == "firearm-magazine" for entity in inspection.entities), "No firearm magazines found in production line"

chest_inventory = inspect_inventory(storage_chest)
assert chest_inventory.get(Prototype.FirearmMagazine, 0) > 0, "No firearm magazines found in storage chest"

print("Automated firearm magazine production line successfully set up!")
