import pytest

import factorio_instance
import functools
from factorio_types import Prototype, Position, Resource
from src.factorio_instance import FactorioInstance

instance = FactorioInstance(address='localhost',
                            bounding_box=200,
                            tcp_port=27000,
                            cache_scripts=False,
                            inventory={
                                'coal': 50,
                                'copper-plate': 50,
                                'iron-plate': 50,
                                'iron-chest': 2,
                                'burner-mining-drill': 3,
                                'electric-mining-drill': 1,
                                'assembling-machine-1': 1,
                                'stone-furnace': 9,
                                'transport-belt': 50,
                                'boiler': 1,
                                'burner-inserter': 32,
                                'pipe': 15,
                                'steam-engine': 1,
                                'small-electric-pole': 10
                        })

from factorio_instance import *
import functools


def verify_research_automation(game):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Set up initial state
            initial_inventory = game.inspect_inventory()
            initial_entities = game.inspect_entities()

            # Run the policy function
            func(*args, **kwargs)

            # Verify the output state
            final_inventory = game.inspect_inventory()
            final_entities = game.inspect_entities()

            # Check if a lab was placed
            lab_placed = any(entity.prototype == Prototype.Lab for entity in final_entities.entities)
            if not lab_placed:
                raise Exception("Lab was not placed")

            # Check if power setup is correct
            power_entities = [Prototype.OffshorePump, Prototype.Boiler, Prototype.SteamEngine,
                              Prototype.SmallElectricPole]
            for entity in power_entities:
                if not any(e.prototype == entity for e in final_entities.entities):
                    raise Exception(f"{entity.name} was not placed")

            # Check if Automation science packs were crafted
            if final_inventory.get(Prototype.AutomationSciencePack, 0) < 10:
                raise Exception("Not enough Automation science packs crafted")

            # Check if research was completed
            lab = next((entity for entity in final_entities.entities if entity.prototype == Prototype.Lab), None)
            if lab is None:
                raise Exception("Lab not found in final entities")

            research_status = game.inspect_entities(lab.position)
            if "AutomationTechnology" not in research_status.completed_technologies:
                raise Exception("Automation technology research was not completed")

            print("Automation technology research objective completed successfully!")

        return wrapper

    return decorator


from factorio_instance import *


def research_automation_technology():
    # Step 1: Gather necessary resources
    iron_ore_position = nearest(Resource.IronOre)
    coal_position = nearest(Resource.Coal)
    copper_ore_position = nearest(Resource.CopperOre)

    harvest_resource(iron_ore_position, quantity=20)
    harvest_resource(coal_position, quantity=10)
    harvest_resource(copper_ore_position, quantity=10)

    # Step 2: Smelt iron and copper ore
    furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
    insert_item(Prototype.Coal, furnace, quantity=5)
    insert_item(Prototype.IronOre, furnace, quantity=10)
    sleep(10)  # Wait for smelting
    iron_plates = extract_item(Prototype.IronPlate, furnace.position, quantity=10)

    insert_item(Prototype.Coal, furnace, quantity=5)
    insert_item(Prototype.CopperOre, furnace, quantity=10)
    sleep(10)  # Wait for smelting
    copper_plates = extract_item(Prototype.CopperPlate, furnace.position, quantity=10)

    # Step 3: Craft basic items
    craft_item(Prototype.IronGearWheel, quantity=5)
    craft_item(Prototype.CopperCable, quantity=10)

    # Step 4: Build a research lab
    lab = place_entity(Prototype.Lab, position=Position(x=2, y=0))

    # Step 5: Create science packs
    craft_item(Prototype.AutomationSciencePack, quantity=10)

    # Step 6: Set up power
    offshore_pump = place_entity(Prototype.OffshorePump, position=Position(x=0, y=5))
    boiler = place_entity(Prototype.Boiler, position=Position(x=2, y=5))
    steam_engine = place_entity(Prototype.SteamEngine, position=Position(x=4, y=5))

    connect_entities(offshore_pump, boiler, connection_type=Prototype.Pipe)
    connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

    insert_item(Prototype.Coal, boiler, quantity=5)

    power_pole = place_entity(Prototype.SmallElectricPole, position=Position(x=3, y=3))
    connect_entities(steam_engine, power_pole)
    connect_entities(power_pole, lab)

    # Step 7: Initiate research
    set_entity_recipe(lab, Prototype.AutomationTechnology)
    insert_item(Prototype.AutomationSciencePack, lab, quantity=10)

    # Step 8: Wait for research completion
    sleep(60)  # Wait for research to complete (adjust time as needed)

    # Step 9: Confirm completion
    research_status = inspect_entities(lab.position)
    if "AutomationTechnology" in research_status.completed_technologies:
        print("Automation technology research completed successfully!")
    else:
        raise Exception("Failed to complete Automation technology research")


research_automation_technology(instance)
# Example usage:
result = craft_and_place_transport_belts(instance, num_belts=5, start_position=Position(x=0, y=0))
print(f"Transport belts crafted and placed successfully: {result}")