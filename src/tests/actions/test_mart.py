from factorio_instance import FactorioInstance

inventory = {
        'iron-plate': 50,
    }
instance = FactorioInstance(address='localhost',
                            bounding_box=200,
                            tcp_port=27015,
                            fast=True,
                            inventory=inventory)
test_string_1 = '# Step 1: Gather resources\niron_ore_needed = 2 * 3  # 3 iron ore per belt (2 for gear, 1 for plate)\nfor _ in range(iron_ore_needed):\n    harvest_resource(nearest(Resource.IronOre))'
test_string = '\nfrom factorio_instance import *\n\ndef craft_transport_belts(num_belts: int = 2) -> bool:\n    # Step 1: Gather resources\n    iron_ore_needed = num_belts * 3  # 3 iron ore per belt (2 for gear, 1 for plate)\n    for _ in range(iron_ore_needed):\n        harvest_resource(nearest(Resource.IronOre))\ncraft_transport_belts(2)'
score, goal, result = instance.eval_with_error(test_string_1, timeout=10)
print(result)