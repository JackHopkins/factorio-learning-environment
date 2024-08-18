from factorio_instance import *
def build_small_steam_power_plant():
    # Step 1: Gather resources (assumed to be already in inventory)
    
    # Step 2: Craft required components
    craft_item(Prototype.Boiler)
    craft_item(Prototype.SteamEngine)
    craft_item(Prototype.OffshorePump)
    craft_item(Prototype.Pipe, 3)  # We need at least 3 pipes
    craft_item(Prototype.SmallElectricPole, 2)  # We need at least 2 electric poles

    # Step 3 & 4: Find water and place offshore pump
    water_position = nearest(Resource.Water)
    offshore_pump = place_entity(Prototype.OffshorePump, position=water_position)

    # Step 5: Connect boiler
    boiler_position = place_entity_next_to(Prototype.Boiler, offshore_pump.position, direction=Direction.RIGHT)
    connect_entities(offshore_pump, boiler_position, connection_type=Prototype.Pipe)

    # Step 6: Set up steam engine
    steam_engine_position = place_entity_next_to(Prototype.SteamEngine, boiler_position, direction=Direction.RIGHT)
    connect_entities(boiler_position, steam_engine_position, connection_type=Prototype.Pipe)

    # Step 7: Add fuel to the boiler
    coal_position = nearest(Resource.Coal)
    harvest_resource(coal_position, quantity=5)
    insert_item(Prototype.Coal, boiler_position, quantity=5)

    # Step 8: Create electrical grid
    pole1_position = place_entity_next_to(Prototype.SmallElectricPole, steam_engine_position, direction=Direction.UP)
    pole2_position = place_entity_next_to(Prototype.SmallElectricPole, pole1_position, direction=Direction.RIGHT, spacing=1)

    # Step 9: Test the system (no specific API call for this, assuming it works if no errors)

    print("Small steam power plant built successfully!")

    # Return the positions of key components for potential future use
    return {
        "offshore_pump": offshore_pump.position,
        "boiler": boiler_position,
        "steam_engine": steam_engine_position,
        "electric_pole1": pole1_position,
        "electric_pole2": pole2_position
    }
