from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.instance import GameControl


class RecordingRconClient:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.command_batches: list[dict[str, str]] = []

    def send_command(self, command: str) -> None:
        self.commands.append(command)

    def send_commands(self, commands: dict[str, str]) -> None:
        self.command_batches.append(commands)


def test_new_game_control_authoritatively_unpauses_reused_server() -> None:
    rcon = RecordingRconClient()
    control = GameControl(rcon, render_message_tool=None, reset_speed=10)

    # A fresh controller believes it is unpaused, even when the persistent
    # Factorio server was paused by the previous environment object.
    assert not control.is_paused()
    control.reset_to_defaults()

    assert "/sc game.tick_paused = false" in rcon.commands
    assert rcon.commands[-1] == "/sc game.speed = 10"


def test_pause_is_also_authoritative_when_local_state_is_already_paused() -> None:
    rcon = RecordingRconClient()
    control = GameControl(rcon, render_message_tool=None)

    control.pause()
    control.pause()

    assert rcon.commands.count("/sc game.tick_paused = true") == 2


def test_background_step_uses_headless_surface_commands() -> None:
    rcon = RecordingRconClient()
    env = object.__new__(FactorioGymEnv)
    env.instance = type("Instance", (), {"rcon_client": rcon})()

    env.background_step(step=10)

    commands = rcon.command_batches[0]
    assert "game.surfaces[1]" in commands["kill_cmd"]
    assert "game.surfaces[1]" in commands["chunk_cmd"]
    assert "game.player" not in commands["kill_cmd"]
    assert "game.players[0]" not in commands["chunk_cmd"]
