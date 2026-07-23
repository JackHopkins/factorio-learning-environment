from argparse import Namespace
from unittest.mock import Mock, patch

import pytest

from fle.run import fle_cluster

pytestmark = pytest.mark.no_factorio


@patch("fle.cluster.run_envs.ClusterManager")
def test_fle_cluster_starts_with_defaults(manager_cls):
    manager = Mock()
    manager_cls.return_value = manager

    fle_cluster(Namespace(cluster_command=None, n=None, s=None))

    manager.start.assert_called_once_with(
        num_instances=1,
        scenario="default_lab_scenario",
    )


@patch("fle.cluster.run_envs.ClusterManager")
def test_fle_cluster_passes_start_options(manager_cls):
    manager = Mock()
    manager_cls.return_value = manager

    fle_cluster(Namespace(cluster_command="start", n=3, s="open_world"))

    manager.start.assert_called_once_with(num_instances=3, scenario="open_world")


@patch("fle.cluster.run_envs.ClusterManager")
def test_fle_cluster_dispatches_lifecycle_commands(manager_cls):
    manager = Mock()
    manager_cls.return_value = manager

    fle_cluster(Namespace(cluster_command="stop", n=None, s=None))
    manager.stop.assert_called_once_with()

    fle_cluster(Namespace(cluster_command="restart", n=None, s=None))
    manager.restart.assert_called_once_with()


@patch("fle.cluster.run_envs.ClusterManager")
def test_fle_cluster_dispatches_logs(manager_cls):
    manager = Mock()
    manager_cls.return_value = manager

    fle_cluster(
        Namespace(
            cluster_command="logs",
            cluster_service="factorio_2",
            n=None,
            s=None,
        )
    )

    manager.logs.assert_called_once_with("factorio_2")
