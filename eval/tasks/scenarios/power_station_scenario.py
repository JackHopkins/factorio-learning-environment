from env.src.entities import Direction, Position
from eval.tasks.scenarios.scenario_abc import ScenarioABC
from env.src.game_types import Resource, Prototype
from env.src.instance import FactorioInstance


class PowerStationScenario(ScenarioABC):
    def __init__(self):
        #self.num_drills = num_drills
        pass

    def deploy(self, instance: FactorioInstance):

        instance.initial_inventory = {'stone-furnace': 1, 'burner-mining-drill': 3, 'transport-belt': 100, 'small-electric-pole': 50,
                                      'boiler': 1, 'steam-engine': 1, 'offshore-pump': 4, 'pipe': 100, 'burner-inserter': 50, 'coal': 50}
        instance.reset()

        game = instance.namespace
        #game.craft_item(Prototype.OffshorePump)
        game.move_to(game.nearest(Resource.Water))
        offshore_pump = game.place_entity(Prototype.OffshorePump,
                                          position=game.nearest(Resource.Water))
        boiler = game.place_entity_next_to(Prototype.Boiler,
                                           reference_position=offshore_pump.position,
                                           direction=offshore_pump.direction,
                                           spacing=5)
        water_pipes = game.connect_entities(boiler, offshore_pump, connection_type=Prototype.Pipe)

        steam_engine = game.place_entity_next_to(Prototype.SteamEngine,
                                                 reference_position=boiler.position,
                                                 direction=boiler.direction,
                                                 spacing=5)
        steam_pipes = game.connect_entities(boiler, steam_engine, connection_type=Prototype.Pipe)

        coal_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                  reference_position=boiler.position,
                                                  direction=Direction.DOWN,
                                                  spacing=0)
        coal_inserter = game.rotate_entity(coal_inserter, Direction.UP)
        game.move_to(game.nearest(Resource.Coal))

        burner_mining_drill = game.place_entity(Prototype.BurnerMiningDrill, position=game.nearest(Resource.Coal))
        burner_inserter = game.place_entity_next_to(Prototype.BurnerInserter,
                                                    reference_position=burner_mining_drill.position,
                                                    direction=Direction.DOWN,
                                                    spacing=0)
        burner_inserter = game.rotate_entity(burner_inserter, Direction.UP)
        assert burner_inserter

        belts = game.connect_entities(burner_mining_drill, burner_inserter, connection_type=Prototype.TransportBelt)
        assert len(belts.outputs) == 1

        coal_to_boiler_belts = game.connect_entities(belts, coal_inserter.pickup_position, connection_type=Prototype.TransportBelt)
        assert coal_to_boiler_belts

        assembler = game.place_entity_next_to(Prototype.AssemblingMachine1,
                                              reference_position=steam_engine.position,
                                              direction=Direction.UP,
                                              spacing=5)

        steam_engine_to_assembler_poles = game.connect_entities(assembler, steam_engine, connection_type=Prototype.SmallElectricPole)

        assert steam_engine_to_assembler_poles

        # insert coal into the drill
        burner_mining_drill: BurnerMiningDrill = game.insert_item(Prototype.Coal, burner_mining_drill, 5)