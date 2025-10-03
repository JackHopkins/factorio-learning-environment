import asyncio
import importlib.resources
from typing import List, Dict

from fle.commons.models import ProductionFlows
from fle.env.entities import Position
from fle.env.gym_env.observation import Observation
from fle.env.protocols._mcp.init import state, initialize_session
from fle.env.protocols._mcp import mcp
from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from mcp.server.fastmcp import Image
from mcp.types import ImageContent, Annotations


# ============== RESOURCES ==============
# These are read-only operations that return data


@mcp.resource("fle://entities/{center_x}/{center_y}/{radius}")
async def entities(center_x: str, center_y: str, radius: str) -> List[Dict]:
    """
    Get all entity objects on the map as a resource.
    Use this to get positions, status and other information about the existing factory.
    """
    if not state.active_server:
        raise Exception("No active Factorio server connection. Use `status` first.")

    instance = state.active_server

    try:
        # Convert string parameters to appropriate types
        cx = float(center_x) if center_x != "default" else 0
        cy = float(center_y) if center_y != "default" else 0
        r = float(radius) if radius != "default" else 500

        entities = instance.namespace.get_entities(position=Position(cx, cy), radius=r)
        return [e.model_dump() for e in entities]
    except Exception as e:
        raise Exception(f"Error getting entities: {str(e)}")


@mcp.resource("fle://inventory")
async def inventory() -> Dict:
    """Get your current inventory"""
    if not state.active_server:
        init_result = await initialize_session(None)
        if not state.active_server:
            raise Exception(f"No active Factorio server connection. {init_result}")

        # raise Exception("No active Factorio server connection. Use `status` first to connect.")

    instance = state.active_server

    try:
        inventory = instance.namespaces[0].inspect_inventory()
        return inventory  # .dict()
    except Exception as e:
        raise Exception(f"Error getting inventory: {str(e)}")


@mcp.resource(
    "fle://position",
    name="position",
    description="Gets your current position",
    annotations=Annotations(audience=["assistant"], priority=1),
)
async def position() -> Dict[str, int]:
    """Get your position in the Factorio world"""
    if not state.active_server:
        init_result = await initialize_session(None)
        if not state.active_server:
            raise Exception(f"No active Factorio server connection. {init_result}")

    try:
        position = state.active_server.namespaces[0].player_location
        return {"x": position.x, "y": position.y}
    except Exception as e:
        raise Exception(f"Error getting position: {str(e)}")


@mcp.resource(
    "fle://prototypes",
    name="prototypes",
    description="Gets the names of all entity prototypes in the game",
    annotations=Annotations(audience=["assistant"], priority=1),
)
async def prototypes() -> List[str]:
    """Get the names of all entities available in the game (Prototype objects)"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    # Return list of recipe names
    return [recipe.name for name, recipe in state.recipes.items()]


@mcp.resource("fle://recipe/{prototype}")
async def recipe(prototype: str) -> str:
    """Get details for a specific recipe"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    if prototype not in state.recipes:
        return f"Recipe '{prototype}' not found."

    recipe = state.recipes[prototype]
    import json

    recipe_data = {
        "name": recipe.name,
        "ingredients": recipe.ingredients,
        "results": recipe.results,
        "energy_required": recipe.energy_required,
    }

    return json.dumps(recipe_data, indent=2)


@mcp.resource("fle://api/schema")
async def schema() -> str:
    """Get the full API object model for writing code to interact with Factorio"""
    execution_path = importlib.resources.files("fle") / "env"
    generator = SystemPromptGenerator(str(execution_path))
    return f"\n\n{generator.types()}\n\n{generator.entities()}"


@mcp.resource("fle://api/manual", mime_type="application/json")
async def manuals() -> dict:  # List[str]:
    """Get API documentation for a specific method"""
    execution_path = importlib.resources.files("fle") / "env"
    agent_tools_path = execution_path / "tools" / "agent"

    if not agent_tools_path.exists() or not agent_tools_path.is_dir():
        return {"error": f"Agent tools directory not found at {agent_tools_path}"}

    available_tools = [d.name for d in agent_tools_path.iterdir() if d.is_dir()]

    return {"tools": available_tools}


@mcp.resource("fle://api/manual/{method}")
async def manual(method: str) -> str:
    """Get API documentation for a specific method"""
    execution_path = importlib.resources.files("fle") / "env"
    agent_tools_path = execution_path / "tools" / "agent"

    if not agent_tools_path.exists() or not agent_tools_path.is_dir():
        return f"Error: Agent tools directory not found at {agent_tools_path}"

    available_tools = [d.name for d in agent_tools_path.iterdir() if d.is_dir()]

    if method not in available_tools:
        return (
            f"Error: '{method}' is not a valid agent tool. Available tools: "
            f"{', '.join(sorted(available_tools))}"
        )

    generator = SystemPromptGenerator(str(execution_path))
    return generator.manual(method)


@mcp.resource("fle://status")
async def status() -> str:
    """Check the status of the Factorio server connection"""
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


@mcp.resource("fle://metrics")
async def metrics() -> dict:
    """Production throughput statistics in the world"""
    if not state.active_server:
        await initialize_session(None)

    try:
        res1: Observation = state.gym_env.get_observation()
        flows1: ProductionFlows = res1.flows
        await asyncio.sleep(1)

        res2: Observation = state.gym_env.get_observation()
        flows2: ProductionFlows = res2.flows

        new_flows = ProductionFlows.get_new_flows(flows1, flows2)

        return new_flows.__dict__
    except Exception as e:
        return {
            "error": str(e),
        }


@mcp.resource("fle://warnings")
async def warnings() -> list:
    if not state.active_server:
        await initialize_session(None)

    warnings = state.active_server.get_warnings()

    return warnings


@mcp.resource("fle://render/{center_x}/{center_y}/{radius}")
async def render_at(center_x: str, center_y: str, radius: int = 32) -> ImageContent:
    """
    Get a rendered image of the current factory state as a base64-encoded PNG.

    Args:
        center_x: X coordinate to center on
        center_y: Y coordinate to center on

    Returns:
        Base64-encoded PNG image data
    """
    if not state.active_server:
        raise Exception("No active Factorio server connection. Use status first.")

    instance = state.active_server

    try:
        cx = float(center_x)
        cy = float(center_y)

        try:
            img = instance.namespace._render(position=Position(cx, cy), radius=radius)
        except Exception:
            img = instance.namespace._render_simple(
                position=Position(cx, cy), radius=radius
            )

        if img is None:
            raise Exception(
                "Failed to render: Game state not properly initialized or player entity invalid"
            )

        # Convert to base64

        # buffer = io.BytesIO()
        # img.save(buffer, format='PNG')
        # img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        content = Image(data=img._repr_png_(), format="png").to_image_content()
        # return f"data:image/png;base64,{img_data}"
        return content

    except Exception as e:
        raise Exception(f"Error rendering: {str(e)}")


pass
