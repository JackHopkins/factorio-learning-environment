import json

import pytest

from fle.cluster.run_envs import ComposeGenerator

pytestmark = pytest.mark.no_factorio


def test_bundled_mod_config_is_staged_in_runtime_state(tmp_path):
    generator = ComposeGenerator(state_dir=tmp_path)

    volume = generator._bundled_mods_volume()

    runtime_mods_dir = tmp_path / "mods"
    runtime_mod_list = runtime_mods_dir / "mod-list.json"
    assert volume["source"] == str(runtime_mods_dir.resolve())
    assert volume["target"] == "/opt/factorio/mods"
    assert json.loads(runtime_mod_list.read_text())["mods"][0] == {
        "name": "base",
        "enabled": True,
    }
