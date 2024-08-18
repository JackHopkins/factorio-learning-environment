from factorio_instance import FactorioInstance

inventory = {
        'coal': 50,
        'copper-plate': 50,
        'iron-plate': 50,
        'iron-chest': 1,
        'burner-mining-drill': 1,
        'electric-mining-drill': 1,
        'assembling-machine-1': 1,
        'stone-furnace': 1,
        # 'small-electric-pole': 10,
        'transport-belt': 50,
        'electronic-circuit': 3,
        'iron-gear-wheel': 3,
        'boiler': 1,
        'burner-inserter': 1,
        'steam-engine': 1,
        'pipe': 50
    }

instance = FactorioInstance(address='localhost',
                            bounding_box=200,
                            tcp_port=27015,
                            fast = True,
                            inventory=inventory)

