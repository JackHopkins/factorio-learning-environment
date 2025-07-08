import os
from pathlib import Path
from typing import Dict

from mcp.server.fastmcp import Image
from fle.env.entities import Position
from fle.commons.models.game_state import GameState
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.env.protocols.mcp import mcp
from fle.env.protocols.mcp.init import state, initialize_session


@mcp.tool()
async def render(center_x: float = 0, center_y: float = 0) -> Image:
    """
    Render the current factory state to an image

    Args:
        width: Width of the output image
        height: Height of the output image
        center_x: X coordinate to center on (defaults to factory center)
        center_y: Y coordinate to center on (defaults to factory center)
        zoom: Zoom level (1.0 = normal)
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    instance = state.active_server

    img = instance.namespace._render(position=Position(center_x, center_y))
    return Image(data=img._repr_png_(), format="png")


@mcp.tool()
async def entities(
    center_x: float = 0, center_y: float = 0, radius: float = 500
) -> str:
    """
    Prints out all entities objects on the map. Use this to get positions, status and other information about the existing factory.

    Args:
        center_x: X coordinate to center on (defaults to factory center)
        center_y: Y coordinate to center on (defaults to factory center)
        radius: Radius from center to retrieve entities
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    instance = state.active_server

    entities = instance.namespace.get_entities(
        position=Position(center_x, center_y), radius=radius
    )
    return str(entities)


@mcp.tool()
async def inventory() -> str:
    """
    Prints out your current inventory.
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    instance = state.active_server

    inventory = instance.namespace.inspect_inventory()
    return str(inventory)


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
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    instance = state.active_server

    # Execute the code
    result, score, response = instance.eval(code, timeout=60)

    # Automatically commit the successful state
    current_state = GameState.from_instance(instance)
    commit_id = vcs.commit(current_state, "Auto-commit after code execution", code)
    return f"[commit {commit_id[:8]}]:\n\n{response}"


@mcp.tool()
async def status() -> str:
    """
    Check the status of the Factorio server connection
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


@mcp.tool()
async def get_entity_names():
    """Get the names of all entities available in the game. They correspond to Prototype objects."""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    # Return list of recipe contents with application/json MIME type
    result = []

    # Add each recipe as a separate content
    for name, recipe in state.recipes.items():
        # recipe_data = {
        #     "name": recipe.name,
        #     "ingredients": recipe.ingredients,
        #     "results": recipe.results,
        #     "energy_required": recipe.energy_required
        # }
        result.append(recipe.name)

    return result


@mcp.tool()
async def position() -> str:
    """
    Get your position in the Factorio world.
    """
    if not state.active_server:
        raise Exception(
            "No active Factorio server connection. Use connect_to_factorio_server first."
        )

    position = state.active_server.namespace.player_location
    return position


@mcp.tool()
async def get_recipe(name: str) -> Dict:
    """Get details for a specific recipe"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    if name not in state.recipes:
        return f"Recipe '{name}' not found."

    recipe = state.recipes[name]
    recipe_data = {
        "name": recipe.name,
        "ingredients": recipe.ingredients,
        "results": recipe.results,
        "energy_required": recipe.energy_required,
    }

    return recipe_data


@mcp.tool()
async def schema() -> str:
    """
    Get the full API object model for writing code so that you can interact with Factorio.
    """
    execution_path = (
        Path(os.path.dirname(os.path.realpath(__file__))).parent
        / Path("env")
        / Path("src")
    )
    # Generate the documentation
    generator = SystemPromptGenerator(str(execution_path))
    return f"\n\n{generator.types()}\n\n{generator.entities()}"


@mcp.tool()
async def manual(name: str) -> str:
    """
    Get API documentation for a specific method

    Args:
        name: Name of the method to get documentation for (must be a valid API method)
    """
    # Get the list of available agent tools by checking directories in the agent directory
    execution_path = (
        Path(os.path.dirname(os.path.realpath(__file__))).parent
        / Path("env")
        / Path("src")
    )
    agent_tools_path = execution_path / "tools" / "agent"

    # Verify the agent_tools_path exists
    if not agent_tools_path.exists() or not agent_tools_path.is_dir():
        return f"Error: Agent tools directory not found at {agent_tools_path}"

    # Get all subdirectories (each one should be a tool)
    available_tools = [d.name for d in agent_tools_path.iterdir() if d.is_dir()]

    # Check if the requested method is valid
    if name not in available_tools:
        return (
            f"Error: '{name}' is not a valid agent tool. Available tools: "
            f"{', '.join(sorted(available_tools))}"
        )

    # Generate the documentation
    generator = SystemPromptGenerator(str(execution_path))
    return generator.manual(name)
