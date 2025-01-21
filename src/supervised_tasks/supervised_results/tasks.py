
class TaskConfig:
    """Configuration for a task"""
    def __init__(self,
                 task: str,
                 check_for_completion = True,
                 check_dicts = {},
                 starting_inventory = {}):
        self.task = task
        self.check_for_completion = check_for_completion
        self.check_dicts = check_dicts
        self.starting_inventory = starting_inventory

class OpenEndedTaskConfig:
    """Configuration for a task"""
    def __init__(self,
                 task: str,
                 throughput_entity: str,
                 starting_inventory = {}):
        self.task = task
        self.throughput_entity = throughput_entity
        self.starting_inventory = starting_inventory

PLACEMENT_STARTING_INVENTORY = {"coal": 500, "burner-mining-drill": 10, "wooden-chest": 10, "burner-inserter": 10, "transport-belt": 500,
                                "stone-furnace": 10, "pipe": 10, "boiler": 4, "offshore-pump": 3, "steam-engine": 2,
                                "iron-gear-wheel": 22, "iron-plate": 19, "copper-plate": 52, "electronic-circuit": 99,
                                "iron-ore": 62, "stone": 50, "electric-mining-drill": 10, "small-electric-pole": 500, "pipe": 100,
                                "assembling-machine-1": 5}

TASKS = {"simple_crafting":{
                            "coal": TaskConfig(
                                task="Mine 5 coal",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"coal", "quantity": 5}]),
                            "copper_plate": TaskConfig(
                                task="Get 3 copper plates",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"copper-plate", "quantity": 3}]),
                            "electronic_circuits": TaskConfig(
                                task="Craft 15 electronic circuits",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"electronic-circuit", "quantity": 6}]),
                            "iron_plates": TaskConfig(
                                task="Get 10 iron plates",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"iron-plate", "quantity": 10}]),
                            "iron_gear_wheels": TaskConfig(
                                task="Craft 20 iron gear wheels",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"iron-gear-wheel", "quantity": 20}]),
                            },
        "medium_crafting": {
                            "lab": TaskConfig(
                            task="Craft one lab. Do not put it down, just craft it",
                            check_for_completion=True,
                            check_dicts=[{"task_type": "craft", "item":"lab", "quantity": 1}]),
                            "burner_mining_drill": TaskConfig(
                            task="Craft one burner mining drill. Do not put it down, just craft it",
                            check_for_completion=True,
                            check_dicts=[{"task_type": "craft", "item":"burner-mining-drill", "quantity": 1}]),
                            #"assembly_machine_1": TaskConfig(
                            #task="Craft two assembly machine ones",
                            #check_for_completion=True,
                            #check_dicts=[{"task_type": "craft", "item":"assembling-machine-1", "quantity": 2}]),
                            "gun_turret": TaskConfig(
                            task="Craft four gun turrets. Do not put them down, just craft them",
                            check_for_completion=True,
                            check_dicts=[{"task_type": "craft", "item":"gun-turret", "quantity": 4}]),
                            },
        "set_crafting": {
                                "mine_setup": TaskConfig(
                                task="Craft one burner mining drill, one burner inserter and 20 transport belts",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"burner-mining-drill", "quantity": 1},
                                             {"task_type": "craft", "item":"burner-inserter", "quantity": 1},
                                             {"task_type": "craft", "item":"transport-belt", "quantity": 20}]),
                                "electricity_setup": TaskConfig(
                                task="Craft one offshore pump, one boiler, one steam engine and 40 pipes",
                                check_for_completion=True,
                                check_dicts=[{"task_type": "craft", "item":"boiler", "quantity": 1},
                                             {"task_type": "craft", "item":"offshore-pump", "quantity": 1},
                                             {"task_type": "craft", "item":"steam-engine", "quantity": 1},
                                             {"task_type": "craft", "item":"pipe", "quantity": 40}]),
                                },
        "medium_automatic_structures": {
                                        "coal_mine": TaskConfig(
                                        task="Create an automatic coal mine that produces 35 coal per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 35}]),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine that produces 35 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 35}]),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 35 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 35}]),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic copper ore mine with one electric mining drill into a chest",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-ore", "quantity": 1},
                                        #             {"task_type": "production_flows_output", "item":"steam", "quantity": 1},
                                        #             {"task_type": "production_flows_input", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
        "simple_automatic_structures": {
                                        "coal_mine": TaskConfig(
                                        task="Create an automatic coal mine with one burner mining drill into a chest",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 1}]),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine with one burner mining drill into a chest",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 1}]),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine with one burner mining drill",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 1}]),
                                        #"steam_setup": TaskConfig(
                                        #task="Create a working electricity generation setup. The task is completed when the setup is generating energy, do not connect it to a network",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "production_flows_output", "item":"steam", "quantity": 1}]),
                                        },
        "simple_automatic_structures_placing": {
                                        #"coal_mine": TaskConfig(
                                        #task="Create an automatic coal mine with one burner mining drill into a chest",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine with one burner mining drill into a chest",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine with one mining drill",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"steam_setup": TaskConfig(
                                        #task="Create a working electricity generation setup. The task is completed when the setup is generating energy, do not connect it to a network",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "production_flows_output", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron_gear_wheel_mine": TaskConfig(
                                        task="Create an automatic iron gear wheel factory with one mining drill",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"iron-gear-wheel", "quantity": 1}],
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
        "medium_automatic_structures_placing": {
                                        "coal_mine": TaskConfig(
                                        task="Create an automatic coal mine that produces 35 coal per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 35}],
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine that produces 35 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 35}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 35 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 35}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic copper ore mine with one electric mining drill into a chest",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-ore", "quantity": 1},
                                        #             {"task_type": "production_flows_output", "item":"steam", "quantity": 1},
                                        #             {"task_type": "production_flows_input", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
            "hard_automatic_structures_placing": {
                                        #"coal_mine": TaskConfig(
                                        #task="Create an automatic coal mine that produces 70 coal per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 70}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine that produces 70 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 70}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "copper_plate_mine": TaskConfig(
                                        task="Create an automatic copper plate mine that produces 70 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 70}],
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 35 copper ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-ore", "quantity": 35},
                                        #             {"task_type": "production_flows_output", "item":"steam", "quantity": 1},
                                        #             {"task_type": "production_flows_input", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic iron gear wheel structure that produces 1 iron gear wheel per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-gear-wheel", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
                    "hard_automatic_structures": {
                                        #"coal_mine": TaskConfig(
                                        #task="Create an automatic coal mine that produces 70 coal per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 70}],
                                        #),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine that produces 70 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 70}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 70 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 70}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 35 copper ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-ore", "quantity": 35},
                                        #             {"task_type": "production_flows_output", "item":"steam", "quantity": 1},
                                        #             {"task_type": "production_flows_input", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic iron gear wheel structure that produces 1 iron gear wheel per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-gear-wheel", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
                    "very_hard_automatic_structures_placing": {
                                        "coal_mine": TaskConfig(
                                        task="Create an automatic coal mine that produces 140 coal per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 140}],
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"iron_mine": TaskConfig(
                                        #task="Create an automatic iron ore mine that produces 140 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 140}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 70 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-plate", "quantity": 70}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic copper plate mine that produces 35 copper ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"copper-ore", "quantity": 35},
                                        #             {"task_type": "production_flows_output", "item":"steam", "quantity": 1},
                                        #             {"task_type": "production_flows_input", "item":"steam", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"electric_copper_ore_mine": TaskConfig(
                                        #task="Create an automatic iron gear wheel structure that produces 1 iron gear wheel per 60 ingame seconds",
                                        #check_for_completion=True,
                                        #check_dicts=[{"task_type": "dynamic", "item":"iron-gear-wheel", "quantity": 1}],
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },

        "random_safety_shit": {
                                        "iron_mine": TaskConfig(
                                        task="Create an automatic iron ore mine with one burner mining drill into a chest. The map already has a working copper ore mine from another agent",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"iron-ore", "quantity": 1}]),
                                        },

        "open_ended": {
                                        "coal_mine": OpenEndedTaskConfig(
                                        task="Create as large of a coal factory as possible during the given steps. Useful information for this task: One burner mining drill mines 5 resources and one electric mining drill mines 10 resources per 20 ingame seconds.",
                                        throughput_entity="coal",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": OpenEndedTaskConfig(
                                        #task="Create as large of a copper plate factory as possible in the given steps. Useful information for this task: One burner mining drill mines 5 resources and one electric mining drill mines 10 resources per 20 ingame seconds. One stone furnace smelts 6 copper plates per 20 ingame seconds",
                                        #throughput_entity="copper-plate",
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
        "open_ended_v2": {
                                        "coal_mine": OpenEndedTaskConfig(
                                        task="Create a factory that produces coal during the given steps. Start off simple, make sure that it works and then improve on the factory. Useful information for this task: One burner mining drill mines 5 resources and one electric mining drill mines 10 resources per 20 ingame seconds.",
                                        throughput_entity="coal",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        #"copper_plate_mine": OpenEndedTaskConfig(
                                        #task="Create as large of a copper plate factory as possible in the given steps. Useful information for this task: One burner mining drill mines 5 resources and one electric mining drill mines 10 resources per 20 ingame seconds. One stone furnace smelts 6 copper plates per 20 ingame seconds",
                                        #throughput_entity="copper-plate",
                                        #starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        },
        "iron_mine_thresholds": {
                                        "iron_mine_1_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 1 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron_mine_32_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 32 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron_mine_64_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 64 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron_mine_128_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 128 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
        },
        "iron_mine_thresholds_scratch": {
                                        "iron_mine_1_scratch": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 1 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore"),
                                        "iron_mine_32_scratch": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 32 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore"),
                                        "iron_mine_64_scratch": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 64 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore"),
                                        "iron_mine_128_scratch": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that produces 128 iron ore per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.",
                                        throughput_entity="iron-ore"),
        },
        "copper_plate_thresholds_placement": {
                                        "copper_plate_mine_1_placement": OpenEndedTaskConfig(
                                        task="Create an automatic copper plate mine that produces 1 copper plate per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "copper_plate_mine_32_placement": OpenEndedTaskConfig(
                                        task="Create an automatic copper plate mine that produces 32 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "copper_plate_mine_64_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that creates 64 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "copper_plate_mine_128_placement": TaskConfig(
                                        task="Create an automatic coal mine that produces 128 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 128}],
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
        },
        "copper_plate_thresholds_scratch": {
                                        "copper_plate_mine_1_placement": OpenEndedTaskConfig(
                                        task="Create an automatic copper plate mine that produces 1 copper plate per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        ),
                                        "copper_plate_mine_32_placement": OpenEndedTaskConfig(
                                        task="Create an automatic copper plate mine that produces 32 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        ),
                                        "copper_plate_mine_64_placement": OpenEndedTaskConfig(
                                        task="Create an automatic iron ore mine that creates 64 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        throughput_entity="copper-plate",
                                        ),
                                        "copper_plate_mine_128_placement": TaskConfig(
                                        task="Create an automatic coal mine that produces 128 copper plates per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds. One stone furnace smelts 18 copper plates per 60 ingame seconds",
                                        check_for_completion=True,
                                        check_dicts=[{"task_type": "dynamic", "item":"coal", "quantity": 128}],
                                        ),
        },
        "iron_gear_wheel_thresholds_placement": {
                                        "iron-gear-wheel_mine_placement_1": OpenEndedTaskConfig(
                                        task="Create an automatic iron gear wheel factory that produces 1 iron gear wheel per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 iron gear wheel per 60 ingame seconds",
                                        throughput_entity="iron-gear-wheel",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron-gear-wheel_mine_placement_32": OpenEndedTaskConfig(
                                        task="Create an automatic iron gear wheel factory that produces 32 iron gear wheel per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 iron gear wheel per 60 ingame seconds",
                                        throughput_entity="iron-gear-wheel",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "iron-gear-wheel_mine_placement_64": OpenEndedTaskConfig(
                                        task="Create an automatic iron gear wheel factory that produces 64 iron gear wheel per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 iron gear wheel per 60 ingame seconds",
                                        throughput_entity="iron-gear-wheel",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
        },
        "electronic_circuit_thresholds_placement": {
                                        "electronic_circuit_mine_placement_1": OpenEndedTaskConfig(
                                        task="Create an automatic electronic circuit factory that produces 1 electronic circuit per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 electronic-circuits per 60 ingame seconds",
                                        throughput_entity="electronic-circuit",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "electronic_circuit_mine_placement_32": OpenEndedTaskConfig(
                                        task="Create an automatic electronic circuit factory that produces 32 electronic circuit per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 electronic-circuits per 60 ingame seconds",
                                        throughput_entity="electronic-circuit",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "electronic_circuit_mine_placement_64": OpenEndedTaskConfig(
                                        task="Create an automatic electronic circuit factory that produces 64 electronic circuit per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 electronic-circuits per 60 ingame seconds",
                                        throughput_entity="electronic-circuit",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
                                        "electronic_circuit_mine_placement_128": OpenEndedTaskConfig(
                                        task="Create an automatic electronic circuit factory that produces 128 electronic circuit per 60 ingame seconds. Useful information for this task: One burner mining drill mines 15 resources and one electric mining drill mines 30 resources per 60 ingame seconds.  One stone furnace smelts 18 iron plates per 60 ingame seconds and one assembling machine crafts 60 electronic-circuits per 60 ingame seconds",
                                        throughput_entity="electronic-circuit",
                                        starting_inventory=PLACEMENT_STARTING_INVENTORY),
        }

        }