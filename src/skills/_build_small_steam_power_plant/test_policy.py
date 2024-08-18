from factorio_instance import *
def test_build_small_steam_power_plant():
    # Check for the presence of required entities
    offshore_pump = get_entity(Prototype.OffshorePump, nearest(Prototype.OffshorePump))
    boiler = get_entity(Prototype.Boiler, nearest(Prototype.Boiler))
    steam_engine = get_entity(Prototype.SteamEngine, nearest(Prototype.SteamEngine))
    electric_pole = get_entity(Prototype.SmallElectricPole, nearest(Prototype.SmallElectricPole))

    if not all([offshore_pump, boiler, steam_engine, electric_pole]):
        print("Missing one or more required entities")
        return False

    # Check connections
    pipes_pump_to_boiler = connect_entities(offshore_pump, boiler, Prototype.Pipe)
    pipes_boiler_to_engine = connect_entities(boiler, steam_engine, Prototype.Pipe)

    if not (pipes_pump_to_boiler and pipes_boiler_to_engine):
        print("Entities are not properly connected with pipes")
        return False

    # Check if boiler has fuel
    boiler_inventory = inspect_inventory(boiler)
    if not (boiler_inventory.get(Prototype.Coal, 0) > 0 or boiler_inventory.get(Resource.Wood, 0) > 0):
        print("Boiler does not have fuel")
        return False

    # Check if steam engine is producing electricity
    entities_around_engine = inspect_entities(steam_engine.position, radius=5)
    electricity_network = next((entity for entity in entities_around_engine if entity.get('name') == 'electric-network'), None)
    
    if not electricity_network or electricity_network.get('energy', 0) <= 0:
        print("Steam engine is not producing electricity")
        return False

    print("Small steam power plant built successfully!")
    return True
