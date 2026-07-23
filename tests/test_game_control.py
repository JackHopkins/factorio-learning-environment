from unittest.mock import Mock, call

import pytest

from fle.env.instance import GameControl

pytestmark = pytest.mark.no_factorio


def test_unpause_asserts_remote_state_when_local_cache_says_unpaused():
    rcon = Mock()
    control = GameControl(rcon, render_message_tool=None)
    control._speed = 10
    control._is_paused = False

    control.unpause()

    assert rcon.send_command.call_args_list == [
        call("/sc game.tick_paused = false"),
        call("/sc game.speed = 10"),
    ]
