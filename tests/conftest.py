import os
import sys
from pathlib import Path

import pytest

from fle.commons.cluster_ips import get_local_container_ips
from fle.env import FactorioInstance

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


@pytest.fixture(scope="session")
def instance(pytestconfig, worker_id):
    # from gym import FactorioInstance
    ips, udp_ports, tcp_ports = get_local_container_ips()
    # --- Parallel mapping (pytest-xdist) ---
    # Docs-backed approach:
    # - Use the built-in `worker_id` fixture to identify the worker ("gw0", "gw1", or "master").  [xdist how-to]
    # - Use PYTEST_XDIST_WORKER_COUNT for total workers when present.         [xdist how-to]
    # Ref: https://pytest-xdist.readthedocs.io/en/stable/how-to.html#identifying-the-worker-process-during-a-test
    xdist_count_env = os.environ.get("PYTEST_XDIST_WORKER_COUNT")
    try:
        opt_numproc = pytestconfig.getoption("numprocesses")
    except Exception:
        opt_numproc = None

    if xdist_count_env and xdist_count_env.isdigit():
        num_workers = int(xdist_count_env)
    elif isinstance(opt_numproc, int) and opt_numproc > 0:
        num_workers = opt_numproc
    else:
        num_workers = 1

    # Determine the zero-based index for this worker.
    if worker_id == "master":
        worker_index = 0
    elif worker_id.startswith("gw") and worker_id[2:].isdigit():
        worker_index = int(worker_id[2:])
    else:
        worker_index = 0

    ports_sorted = sorted(tcp_ports)

    if num_workers > 1:
        if len(ports_sorted) < num_workers:
            raise pytest.UsageError(
                f"pytest -n {num_workers} requested, but only {len(ports_sorted)} Factorio TCP ports were found: "
                f"{ports_sorted}. Start {num_workers} servers, e.g. './run-envs.sh start -n {num_workers}'."
            )
        selected_port = ports_sorted[worker_index]
    else:
        # Single-process run: allow explicit override via env, else use last discovered port.
        port_env = os.getenv("FACTORIO_RCON_PORT")
        if port_env:
            selected_port = int(port_env)
        else:
            if not ports_sorted:
                raise pytest.UsageError(
                    "No Factorio TCP ports discovered. Did you start the headless server?"
                )
            selected_port = ports_sorted[-1]
    try:
        instance = FactorioInstance(
            address="localhost",
            all_technologies_researched=True,
            tcp_port=selected_port,  # prefer env (CI) else last discovered
            cache_scripts=True,
            fast=True,
            inventory={
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
            },
        )
        instance.set_speed(10)
        # Keep a canonical copy of the default test inventory to restore between tests
        try:
            instance.default_initial_inventory = dict(instance.initial_inventory)
        except Exception:
            instance.default_initial_inventory = instance.initial_inventory
        yield instance
    except Exception as e:
        raise e
    finally:
        # Cleanup RCON connections to prevent connection leaks
        if "instance" in locals():
            instance.cleanup()


# # Reset state between tests without recreating the instance
@pytest.fixture(autouse=True)
def _reset_between_tests(instance):
    """
    Ensure clean state between tests without reloading Lua/scripts.
    """
    # Restore the default inventory in case a previous test changed it
    if hasattr(instance, "default_initial_inventory"):
        try:
            instance.initial_inventory = dict(instance.default_initial_inventory)
        except Exception:
            instance.initial_inventory = instance.default_initial_inventory
    instance.reset(reset_position=True)
    yield


# Provide a lightweight fixture that yields the game namespace derived from the
# already-maintained `instance`. Many tests only need `namespace` and not the
# full `instance`.
@pytest.fixture()
def namespace(instance):
    yield instance.namespace


# Backwards-compatible alias used by many tests; simply yields `namespace`.
@pytest.fixture()
def game(namespace):
    yield namespace


# Flexible configuration fixture for tests that need to tweak flags like
# `all_technologies_researched` and/or inventory in one step and receive a fresh namespace.
@pytest.fixture()
def configure_game(instance):
    def _configure_game(
        inventory: dict | None = None,
        merge: bool = False,
        persist_inventory: bool = False,
        *,
        reset_position: bool = True,
        all_technologies_researched: bool = True,
    ):
        instance.reset(
            reset_position=reset_position,
            all_technologies_researched=all_technologies_researched,
        )

        # Apply inventory first, so the subsequent reset reflects desired items
        if inventory is not None:
            print(f"Setting inventory: {inventory}")
            if merge:
                try:
                    updated = {**instance.initial_inventory, **inventory}
                except Exception:
                    updated = dict(instance.initial_inventory)
                    updated.update(inventory)
            else:
                updated = dict(inventory)
            if persist_inventory:
                instance.initial_inventory = updated
            instance.set_inventory(updated)

        return instance.namespace

    return _configure_game
