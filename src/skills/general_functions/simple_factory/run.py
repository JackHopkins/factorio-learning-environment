from factorio_instance import FactorioInstance

factorio = FactorioInstance(address='localhost',
                                    bounding_box=200,
                                    tcp_port=27000,
                                    cache_scripts=False,
                                    fast=True,
                                    inventory={
                                        'coal': 50,
                                        'copper-plate': 50,
                                        'iron-plate': 50,
                                        'iron-chest': 2,
                                        'burner-mining-drill': 3,
                                        'electric-mining-drill': 1,
                                        'assembling-machine-1': 1,
                                        'stone-furnace': 9,
                                        'transport-belt': 80,
                                        'boiler': 1,
                                        'burner-inserter': 32,
                                        'pipe': 15,
                                        'steam-engine': 1,
                                        'small-electric-pole': 10,
                                        'wooden-chest': 5
                                })

# Execute a snippet file
try:
    # Execute a snippet file
    factorio.run_snippet_file_in_factorio_env('snippet.py')
finally:
    # Ensure cleanup is called even if an exception occurs
    factorio.cleanup()