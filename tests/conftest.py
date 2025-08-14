import os
import sys
from pathlib import Path

import pytest

from fle.env.game import FactorioInstance
from fle.env.game.factorio_client import FactorioClient
from fle.services.docker.config import DockerConfig

# Add the src directory to the Python path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# Get the project root directory
project_root = Path(__file__).parent.parent.parent

# Add the project root and src to Python path
# if str(project_root) not in sys.path:
#     sys.path.insert(0, str(project_root))
# if str(project_root / 'src') not in sys.path:
#     sys.path.insert(0, str(project_root / 'src'))

@pytest.fixture()
def instance():
    """Create a connected FactorioInstance using the new FactorioClient API.

    Requires a running local Factorio headless container started via the docker manager.
    If none are running, the tests using this fixture will be skipped.
    """
    config = DockerConfig()

    # Read RCON password used by the local headless server
    client = FactorioClient(
        instance_id=0,
        rcon_port=config.rcon_port,
        address=config.address,
        rcon_password=config.factorio_password,
        cache_scripts=True,
    )

    inventory = {
        "coal": 50,
        "copper-plate": 50,
        "iron-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 50,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
    }

    inst = None
    try:
        inst = FactorioInstance(
            client=client,
            fast=True,
            inventory=inventory,
        )
        yield inst
    finally:
        if inst is not None:
            inst.cleanup()


@pytest.fixture()
def unresearched_instance():
    """Create a FactorioInstance with no technologies researched.

    Requires a running local Factorio headless container started via the docker manager.
    If none are running, the tests using this fixture will be skipped.
    """
    config = DockerConfig()

    client = FactorioClient(
        instance_id=0,
        rcon_port=config.rcon_port,
        address=config.address,
        rcon_password=config.factorio_password,
        cache_scripts=True,
    )

    inventory = {
        "coal": 50,
        "copper-plate": 50,
        "iron-plate": 50,
        "iron-chest": 2,
        "burner-mining-drill": 3,
        "electric-mining-drill": 1,
        "assembling-machine-1": 1,
        "stone-furnace": 9,
        "transport-belt": 50,
        "boiler": 1,
        "burner-inserter": 32,
        "pipe": 15,
        "steam-engine": 1,
        "small-electric-pole": 10,
    }

    inst = None
    try:
        inst = FactorioInstance(
            client=client,
            fast=True,
            inventory=inventory,
            all_technologies_researched=False,
        )
        yield inst
    finally:
        if inst is not None:
            inst.cleanup()
