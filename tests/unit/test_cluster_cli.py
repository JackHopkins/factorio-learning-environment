"""`fle cluster` on Windows goes through ClusterManager instead of run-envs.sh.

Windows cannot execute the bash script (WinError 193). These tests stub out
ClusterManager, so they need neither Docker nor a Factorio server.
"""

import argparse
import types

import pytest

import fle.cluster.run_envs as run_envs
import fle.run as cli


class FakeManager:
    calls: list = []

    def start(self, num_instances, scenario):
        FakeManager.calls.append(("start", num_instances, scenario))

    def stop(self):
        FakeManager.calls.append(("stop",))

    def restart(self):
        FakeManager.calls.append(("restart",))


@pytest.fixture
def windows(monkeypatch):
    """Pretend to run on Windows and record what the CLI asks the manager to do."""
    FakeManager.calls = []
    monkeypatch.setattr(run_envs, "ClusterManager", FakeManager)
    monkeypatch.setattr(cli, "os", types.SimpleNamespace(name="nt"))

    def fail_subprocess(*a, **k):
        raise AssertionError("run-envs.sh must not be executed on Windows")

    monkeypatch.setattr(cli.subprocess, "run", fail_subprocess)
    return FakeManager.calls


def _args(command=None, n=None, s=None):
    return argparse.Namespace(cluster_command=command, n=n, s=s)


def test_start_defaults_match_run_envs_sh(windows):
    cli.fle_cluster(_args())
    assert windows == [("start", 1, "default_lab_scenario")]


def test_start_with_options(windows):
    cli.fle_cluster(_args("start", n=3, s="open_world"))
    assert windows == [("start", 3, "open_world")]


@pytest.mark.parametrize("command", ["stop", "restart"])
def test_stop_and_restart(windows, command):
    cli.fle_cluster(_args(command))
    assert windows == [(command,)]


def test_help_prints_usage(windows, capsys):
    cli.fle_cluster(_args("help"))
    assert "Usage: fle cluster" in capsys.readouterr().out
    assert windows == []


@pytest.mark.parametrize("n,s", [(0, None), (34, None), (1, "no_such_scenario")])
def test_invalid_input_exits(windows, n, s):
    with pytest.raises(SystemExit):
        cli.fle_cluster(_args("start", n=n, s=s))
    assert windows == []
