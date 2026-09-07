import os
import sys
from functools import wraps
from pathlib import Path

import pytest

from fle.commons.cluster_ips import get_local_container_ips
from fle.env import FactorioInstance


def pytest_configure(config):
    """Route every local Factorio instance to each xdist worker's server."""
    worker_input = getattr(config, "workerinput", None)
    if not worker_input:
        return

    worker_id = worker_input["workerid"]
    worker_index = int(worker_id[2:])
    _, _, tcp_ports = get_local_container_ips()
    cluster_ports = set(tcp_ports)
    selected_port = sorted(cluster_ports)[worker_index]
    os.environ["FACTORIO_RCON_PORT"] = str(selected_port)

    original_init = FactorioInstance.__init__

    @wraps(original_init)
    def worker_scoped_init(self, *args, **kwargs):
        args = list(args)
        if len(args) >= 3:
            if args[2] in cluster_ports:
                args[2] = selected_port
        elif kwargs.get("tcp_port", 27000) in cluster_ports:
            kwargs["tcp_port"] = selected_port
        return original_init(self, *args, **kwargs)

    FactorioInstance.__init__ = worker_scoped_init


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
    # from gymnasium import FactorioInstance
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
                "fast-transport-belt": 10,
                "express-transport-belt": 10,
            },
        )
        instance.set_speed(10.0)
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
def _reset_between_tests(instance, request):
    """
    Ensure clean state between tests without reloading Lua/scripts.
    """
    # If this test explicitly uses `configure_game`, let that fixture perform
    # the reset to avoid double resets and allow per-test options.
    if "configure_game" in getattr(request, "fixturenames", []):
        yield
        return
    # Restore the default inventory in case a previous test changed it
    # Note: ensure_connected() is called inside reset() so we don't need to call it here
    if hasattr(instance, "default_initial_inventory"):
        try:
            instance.initial_inventory = dict(instance.default_initial_inventory)
        except Exception:
            instance.initial_inventory = instance.default_initial_inventory
    instance.reset(reset_position=True)
    yield


@pytest.fixture(autouse=True)
def _restore_destructive_terrain_tests(instance, request, _reset_between_tests):
    """Roll back terrain edits made by render and blueprint setup helpers."""
    test_path = str(request.node.path)
    mutates_terrain = "clear_terrain" in getattr(
        request, "fixturenames", []
    ) or test_path.endswith("tests/blueprints/test_blueprint_based_policies.py")
    if not mutates_terrain:
        yield
        return

    snapshot_command = r"""
local surface = game.surfaces[1]
local snapshot_area = {{-64, -64}, {192, 64}}
storage.pytest_terrain_snapshot = {tiles = {}, entities = {}}
for x = -64, 192 do
    for y = -64, 64 do
        local tile = surface.get_tile(x, y)
        table.insert(storage.pytest_terrain_snapshot.tiles, {
            name = tile.name,
            position = {x = x, y = y}
        })
    end
end
for _, entity in pairs(surface.find_entities_filtered{
    type = {"cliff", "simple-entity", "tree", "resource"}, area = snapshot_area
}) do
    if entity.type ~= "simple-entity" or string.find(entity.name, "rock") then
        local initial = {
        name = entity.name,
        position = {x = entity.position.x, y = entity.position.y}
        }
        if entity.type == "cliff" then
            initial.cliff_orientation = entity.cliff_orientation
        elseif entity.type == "resource" then
            initial.amount = entity.amount
        end
        table.insert(storage.pytest_terrain_snapshot.entities, initial)
    end
end
"""
    instance.rcon_client.send_command("/silent-command " + snapshot_command)
    yield
    restore_command = r"""
local surface = game.surfaces[1]
local snapshot = storage.pytest_terrain_snapshot
if snapshot then
    local snapshot_area = {{-64, -64}, {192, 64}}
    surface.set_tiles(snapshot.tiles, true)
    for _, entity in pairs(surface.find_entities_filtered{
        type = {"cliff", "simple-entity", "tree", "resource"}, area = snapshot_area
    }) do
        if entity.type ~= "simple-entity" or string.find(entity.name, "rock") then
            entity.destroy()
        end
    end
    for _, initial in pairs(snapshot.entities) do
        pcall(function() surface.create_entity(initial) end)
    end
    storage.pytest_terrain_snapshot = nil
end
"""
    instance.rcon_client.send_command("/silent-command " + restore_command)


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
        # Always start from the canonical default inventory to avoid leakage
        # Note: ensure_connected() is called inside reset() so we don't need to call it here
        # from previous tests when this fixture is used.
        if hasattr(instance, "default_initial_inventory"):
            try:
                instance.initial_inventory = dict(instance.default_initial_inventory)
            except Exception:
                instance.initial_inventory = instance.default_initial_inventory

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
            instance.first_namespace._set_inventory(updated)

        return instance.namespace

    return _configure_game
