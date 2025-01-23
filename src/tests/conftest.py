import os
import sys
from pathlib import Path

import pytest

# Add the src directory to the Python path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Get the project root directory
project_root = Path(__file__).parent.parent.parent

# Add the project root and src to Python path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / 'src') not in sys.path:
    sys.path.insert(0, str(project_root / 'src'))

@pytest.fixture()#scope="session")
def instance():
    from src.factorio_instance import FactorioInstance
    try:
        instance = FactorioInstance(address='localhost',
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

