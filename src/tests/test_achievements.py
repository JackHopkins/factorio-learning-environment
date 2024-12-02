import unittest
from factorio_instance import FactorioInstance
from utils import eval_program_with_achievements

def test_achievements_from_scratch():
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory={})

        test_string_1 = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.IronOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.IronOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(5)\nextract_item(Prototype.IronPlate, furnace.position, 10)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string_1)
        ground_truth_achievement = {'static': {'stone-furnace': 1, 'coal': 10, 'stone': 10, 'iron-ore': 10}, 'dynamic': {'iron-plate': 5}}
       
        assert achievements == ground_truth_achievement
        test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(5)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        ground_truth_achievement = {'static': {'stone-furnace': 1, 'coal': 10, 'stone': 10, 'copper-ore': 10}, 'dynamic': {'copper-plate': 5}}
        assert achievements == ground_truth_achievement
        test_string = "pos = nearest(Resource.Stone)\nmove_to(pos)\nharvest_resource(pos, 10)\ncraft_item(Prototype.StoneFurnace, 1)\npos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = nearest(Resource.CopperOre)\nmove_to(pos)\nharvest_resource(pos, 10)\npos = Position(x = 0, y = 0)\nmove_to(pos)\nfurnace = place_entity(Prototype.StoneFurnace, position = pos)\ninsert_item(Prototype.CopperOre, furnace, 5)\ninsert_item(Prototype.Coal, furnace, 5)\nsleep(5)"
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        ground_truth_achievement = {'static': {'stone-furnace': 1, 'coal': 10, 'stone': 10, 'copper-ore': 10}, 'dynamic': {'copper-plate': 5}}
        assert achievements == ground_truth_achievement

def test_achievements_fluid_and_steam():
        """
        This test might fail in some map cases due to place_entity_next_to direction being incompatible with the nearest water source
        This has been tested in fact lab, game speed atleast 5
        """
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory={"offshore-pump":1,
                                           "boiler":1,
                                           "coal":4,
                                           "pipe":30,
                                           "steam-engine":1})

        test_string = "pos = nearest(Resource.Water)\nmove_to(pos)\npump = place_entity(Prototype.OffshorePump, position = pos)\nboiler = place_entity_next_to(Prototype.Boiler, reference_position = pump.position, spacing =2, direction = Direction.UP)\nconnect_entities(pump, boiler, Prototype.Pipe)\nsleep(5)"
        # dynami cwater
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==1
        assert "water" in achievements["dynamic"].keys()

        # add another entity that shouldnt add any achievements
        test_string = "entities = get_entities()\nboiler = [entity for entity in entities if entity.name == 'boiler'][0]\nsteam_engine = place_entity_next_to(Prototype.SteamEngine, reference_position = boiler.position, spacing =2, direction = Direction.UP)"
        # no achievements
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==0

        # Now we connect the steam engine and boiler but dont power boiler so still no achievements
        test_string = "entities = get_entities()\nboiler = [entity for entity in entities if entity.name == 'boiler'][0]\nsteam_engine = [entity for entity in entities if entity.name == 'steam-engine'][0]\nconnect_entities(boiler, steam_engine, Prototype.Pipe)\nsleep(2)"
        # no achievements
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==0

        # Now we add coal and should get dynamic achievements
        test_string = "entities = get_entities()\nboiler = [entity for entity in entities if entity.name == 'boiler'][0]\ninsert_item(Prototype.Coal,boiler, 2)\nsleep(2)"
        # dynamic water and steam
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==2
        assert "water" in achievements["dynamic"].keys()
        assert "steam" in achievements["dynamic"].keys()

        # Now we go and mine some coal
        test_string = "pos = nearest(Resource.Coal)\nmove_to(pos)\nharvest_resource(pos, 10)"
        # We check that we only get the static coal achievement
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==1
        assert len(achievements["dynamic"].keys())==0
        assert "coal" in achievements["static"].keys()
        assert achievements["static"]["coal"]==10


def test_achievements_electricity():
        """
        This test might fail in some map cases due to place_entity_next_to direction being incompatible with the nearest water source
        This has been tested in fact lab, game speed atleast 5
        """
        instance = FactorioInstance(address='localhost',
                                bounding_box=200,
                                tcp_port=27015,
                                fast=True,
                                #cache_scripts=False,
                                inventory={"offshore-pump":1,
                                           "boiler":1,
                                           "coal":4,
                                           "pipe":30,
                                           "steam-engine":1,
                                           "small-electric-pole": 200,
                                           "electric-mining-drill": 2})
        # This just sets it up
        test_string = "pos = nearest(Resource.Water)\nmove_to(pos)\npump = place_entity(Prototype.OffshorePump, position = pos)\nboiler = place_entity_next_to(Prototype.Boiler, reference_position = pump.position, spacing =2, direction = Direction.UP)\nconnect_entities(pump, boiler, Prototype.Pipe)\nsteam_engine = place_entity_next_to(Prototype.SteamEngine, reference_position = boiler.position, spacing =2, direction = Direction.UP)\nconnect_entities(boiler, steam_engine, Prototype.Pipe)\ninsert_item(Prototype.Coal,boiler, 2)\nsleep(5)"
        # run the setup
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)


        # Place a electric mining drill on coal patch
        test_string = "pos = nearest(Resource.IronOre)\nmove_to(pos)\ndrill = place_entity(Prototype.ElectricMiningDrill, position = pos)"
        # We should get no achievements
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==0

        # Now connect the the drill to the steam engine
        test_string = "entities = get_entities()\ndrill = [entity for entity in entities if entity.name == 'electric-mining-drill'][0]\nsteam_engine = [entity for entity in entities if entity.name == 'steam-engine'][0]\nconnect_entities(drill, steam_engine, Prototype.SmallElectricPole)\nsleep(15)"
        # We should get some achievements, namely dynamic iron ore
        _, _, _, achievements = eval_program_with_achievements(instance, test_string)
        assert len(achievements["static"].keys())==0
        assert len(achievements["dynamic"].keys())==1
        assert "iron-ore" in achievements["dynamic"].keys()


if __name__ == '__main__':
    unittest.main()
