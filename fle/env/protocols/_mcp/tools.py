from mcp.server.fastmcp import Image
from mcp.types import ImageContent

from fle.env.entities import Position
from fle.commons.models.game_state import GameState

from fle.env.protocols._mcp.init import state, initialize_session
from fle.env.protocols._mcp import mcp


#
@mcp.tool()
async def render(center_x: float = 0, center_y: float = 0) -> ImageContent:
    """
    Render the current factory state to an image

    Args:
        center_x: X coordinate to center on (defaults to factory center)
        center_y: Y coordinate to center on (defaults to factory center)
    """
    if not state.active_server:
        raise Exception("No active Factorio server connection. Use status first.")

    instance = state.active_server

    try:
        img = instance.namespace._render(position=Position(center_x, center_y))
        if img is None:
            raise Exception(
                "Failed to render: Game state not properly initialized or player entity invalid"
            )
        return Image(data=img._repr_png_(), format="png").to_image_content()
    except Exception as e:
        raise Exception(f"Error rendering: {str(e)}")


@mcp.tool()
async def execute(code: str) -> str:
    """
    Run Python code and automatically commit the result.

    All API methods are already imported into the namespace, so no need to import any Factorio methods or types (e.g Direction, Prototype etc)

    If you are confused about what methods are available, use `ls` followed by `man` to read the manual about a method.

    If you need to debug an error message, use the introspection tools (e.g `cat`) to analyse the *.lua and *.py implementations.

    Args:
        code: Python code to execute
    """
    if not state.active_server:
        await initialize_session(
            None
        )  # "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    instance = state.active_server

    # Execute the code
    result, score, response = instance.eval(code, timeout=60)

    # Automatically commit the successful state
    current_state = GameState.from_instance(instance)
    commit_id = vcs.commit(current_state, "Auto-commit after code execution", code)

    # Update game state file after execution
    try:
        game_state_data = {
            "inventory": instance.namespace.inspect_inventory(),
            "entities": instance.namespace.get_entities(radius=100),
            "score": instance.namespace.score(),
            "game_tick": instance.namespace.game_info.tick,
            "position": instance.namespace.player_location,
            "production_stats": instance.namespace.get_production_stats(),
        }

        import json
        from pathlib import Path

        state_file = Path("/tmp/factorio_game_state.json")
        with open(state_file, "w") as f:
            json.dump(game_state_data, f, default=str)
    except Exception:
        # Don't fail the whole execution just because state file update failed
        pass

    # try:
    #     initial_obs = state.gym_env.unwrapped.get_observation(0)
    #     formatted_obs = BasicObservationFormatter(include_research=False).format(initial_obs).raw_str
    #
    #     observation = formatted_obs
    # except Exception as e:
    #     observation = str(e)
    #
    # lines = response.split("\b")
    return f"[commit {commit_id[:8]}] - stdio:\n{response}\n"


@mcp.tool()
async def reconnect() -> str:
    """
    Reconnect with the Factorio server
    """
    if not state.active_server:
        return await initialize_session(None)

    server_id = state.active_server.tcp_port
    if server_id in state.available_servers:
        server = state.available_servers[server_id]
        vcs = state.get_vcs()
        commits = len(vcs.undo_stack) if vcs else 0

        return (
            f"Connected to Factorio server: {server.name} ({server.address}:{server.tcp_port})\n"
            f"Commit history: {commits} commits"
        )
    else:
        return "Connected to Factorio server"
