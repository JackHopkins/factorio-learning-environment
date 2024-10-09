import pytest
@pytest.fixture(scope="session")
def instance():
    from src.factorio_instance import FactorioInstance
    try:
        instance = FactorioInstance(address='localhost',
                                    bounding_box=200,
                                    tcp_port=27015,
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
        yield instance
    except Exception as e:
        raise e

