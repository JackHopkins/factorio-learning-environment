"""Fixtures for tiered-observation-protocol tests.

Launches a dedicated Factorio container on a random free port with the
open_world scenario from this checkout, and removes it afterward. It never
connects to (or discovers) any already-running FLE cluster server.
"""

import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest
from factorio_rcon import RCONClient

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGE = "factoriotools/factorio:2.0.73"
RCON_PASSWORD = "factorio"
STARTUP_TIMEOUT = 300


@pytest.fixture(autouse=True)
def _reset_between_tests():
    """Shadow the repo-level autouse fixture that connects to the shared FLE
    cluster; these tests run exclusively against their own container."""
    yield


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _docker_ok():
    return (
        shutil.which("docker") is not None
        and subprocess.run(
            ["docker", "info"], capture_output=True, timeout=30
        ).returncode
        == 0
    )


@pytest.fixture(scope="session")
def tiered_rcon():
    """RCON client for a dedicated, isolated tiered-observation server."""
    if not _docker_ok():
        pytest.skip("docker is not available")

    port = _free_port()
    name = f"fle-test-tiered-{port}"
    cluster = REPO_ROOT / "fle" / "cluster"
    emulator = "/bin/box64 " if platform.machine() in ("arm64", "aarch64") else ""
    factorio_cmd = (
        "rm -rf /opt/factorio/data/elevated-rails /opt/factorio/data/quality "
        "/opt/factorio/data/space-age && "
        f"exec {emulator}/opt/factorio/bin/x64/factorio "
        "--start-server-load-scenario open_world --port 34197 "
        "--server-settings /opt/factorio/config/server-settings.json "
        "--map-gen-settings /opt/factorio/config/map-gen-settings.json "
        "--map-settings /opt/factorio/config/map-settings.json "
        "--rcon-port 27015 "
        f'--rcon-password "{RCON_PASSWORD}" '
        "--server-adminlist /opt/factorio/config/server-adminlist.json "
        "--mod-directory /opt/factorio/mods --map-gen-seed 44340"
    )
    run = subprocess.run(
        [
            "docker", "run", "-d", "--name", name,
            "-p", f"127.0.0.1:{port}:27015",
            "-v", f"{cluster / 'scenarios'}:/opt/factorio/scenarios",
            "-v", f"{cluster / 'config'}:/opt/factorio/config",
            "-v", f"{cluster / 'mods'}:/opt/factorio/mods",
            "--entrypoint", "/bin/sh",
            IMAGE, "-c", factorio_cmd,
        ],
        capture_output=True,
        text=True,
    )
    if run.returncode != 0:
        pytest.skip(f"could not start factorio container: {run.stderr.strip()}")

    rc = None
    try:
        deadline = time.time() + STARTUP_TIMEOUT
        last_error = None
        while time.time() < deadline:
            try:
                rc = RCONClient("127.0.0.1", port, RCON_PASSWORD)
                rc.connect()
                rc.send_command("/sc rcon.print(1)")
                break
            except Exception as e:  # noqa: BLE001 - retry until server is up
                last_error = e
                rc = None
                time.sleep(3)
        if rc is None:
            logs = subprocess.run(
                ["docker", "logs", "--tail", "15", name],
                capture_output=True, text=True,
            ).stdout
            raise RuntimeError(
                f"factorio server did not come up in {STARTUP_TIMEOUT}s: "
                f"{last_error}\n{logs}"
            )

        loaded = rc.send_command("/sc rcon.print(type(obs_diff_drain))")
        assert loaded == "function", (
            "observation_diff.lua not loaded by the open_world scenario "
            f"(type(obs_diff_drain) == {loaded!r})"
        )
        rc.send_command("/sc game.speed = 10")
        yield rc
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)