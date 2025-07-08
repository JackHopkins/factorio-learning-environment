import json
import os
from pathlib import Path
from typing import Dict

from fle.env.utils.controller_loader.system_prompt_generator import (
    SystemPromptGenerator,
)
from fle.env.protocols.mcp import mcp
from fle.env.protocols.mcp.init import state

HOST = "fle"


@mcp.resource(
    HOST + "://server/{instance_id}/entities",
    name="Server Entities",
    mime_type="application/json",
)
async def get_server_entities(instance_id: int):
    """Get all entities for a specific Factorio server"""
    # Convert to int
    instance_id = int(instance_id)

    # Check if server exists
    if instance_id not in state.available_servers:
        return f"No Factorio server found with instance ID {instance_id}"

    # Check if server is active
    server = state.available_servers[instance_id]
    if not server.is_active:
        return f"Factorio server with instance ID {instance_id} is not active"

    # Make sure we have data for this server
    if (
        instance_id not in state.server_entities
        or not state.server_entities[instance_id]
    ):
        await state.refresh_game_data(instance_id)

    # Get entities for this server
    entities = state.server_entities.get(instance_id, {})

    return json.dumps(
        {
            id: {
                "id": e.id,
                "name": e.name,
                "position": e.position,
                "direction": e.direction,
                "health": e.health,
            }
            for id, e in entities.items()
        },
        indent=2,
    )


@mcp.resource(
    HOST
    + "://server/{instance_id}/entities/{top_left_x}/{top_left_y}/{bottom_right_x}/{bottom_right_y}",
    name="Entities in Area",
    mime_type="application/json",
)
async def get_server_entities_in_area(
    instance_id: int,
    top_left_x: float,
    top_left_y: float,
    bottom_right_x: float,
    bottom_right_y: float,
):
    """Get entities within a specified area for a specific Factorio server"""
    # Convert to int and float
    instance_id = int(instance_id)
    top_left_x = float(top_left_x)
    top_left_y = float(top_left_y)
    bottom_right_x = float(bottom_right_x)
    bottom_right_y = float(bottom_right_y)

    # Check if server exists
    if instance_id not in state.available_servers:
        return f"No Factorio server found with instance ID {instance_id}"

    # Check if server is active
    server = state.available_servers[instance_id]
    if not server.is_active:
        return f"Factorio server with instance ID {instance_id} is not active"

    # Make sure we have data for this server
    if (
        instance_id not in state.server_entities
        or not state.server_entities[instance_id]
    ):
        await state.refresh_game_data(instance_id)

    # Get entities for this server
    entities = state.server_entities.get(instance_id, {})

    # Filter by area
    filtered_entities = {
        id: e
        for id, e in entities.items()
        if (
            top_left_x <= e.position["x"] <= bottom_right_x
            and top_left_y <= e.position["y"] <= bottom_right_y
        )
    }

    return json.dumps(
        {
            id: {
                "id": e.id,
                "name": e.name,
                "position": e.position,
                "direction": e.direction,
                "health": e.health,
            }
            for id, e in filtered_entities.items()
        },
        indent=2,
    )


@mcp.resource(
    HOST + "://server/{instance_id}/resources/{name}",
    name="Server Resource Patches",
    mime_type="application/json",
)
async def get_server_resources(instance_id: int, name: str):
    """Get all patches of a specific resource for a Factorio server"""
    # Convert to int
    instance_id = int(instance_id)

    # Check if server exists
    if instance_id not in state.available_servers:
        return f"No Factorio server found with instance ID {instance_id}"

    # Check if server is active
    server = state.available_servers[instance_id]
    if not server.is_active:
        return f"Factorio server with instance ID {instance_id} is not active"

    # Make sure we have data for this server
    if (
        instance_id not in state.server_resources
        or not state.server_resources[instance_id]
    ):
        await state.refresh_game_data(instance_id)

    # Get resources for this server
    resources = state.server_resources.get(instance_id, {})

    # Filter by resource name
    filtered_resources = {id: r for id, r in resources.items() if r.name == name}

    return {
        id: {"name": r.name, "position": r.position, "amount": r.amount, "size": r.size}
        for id, r in filtered_resources.items()
    }


# Global recipe resources - not scoped to a server
@mcp.resource(f"{HOST}://recipes", name="All Recipes", mime_type="application/json")
async def get_all_recipes():
    """Get all available recipes - global across all servers"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    # Return list of recipe contents with application/json MIME type
    result = []

    # Add each recipe as a separate content
    for name, recipe in state.recipes.items():
        recipe_data = {
            "name": recipe.name,
            "ingredients": recipe.ingredients,
            "results": recipe.results,
            "energy_required": recipe.energy_required,
        }

        result.append(recipe_data)

    return result


@mcp.resource(
    f"{HOST}" + "://recipe/{name}", name="Recipe Details", mime_type="application/json"
)
async def get_recipe(name: str) -> Dict:
    """Get details for a specific recipe - global across all servers"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    if name not in state.recipes:
        return {
            "uri": HOST + f"://recipe/{name}/error",
            "text": f"Recipe '{name}' not found.",
            "mimeType": "text/plain",
        }

    recipe = state.recipes[name]
    recipe_data = {
        "name": recipe.name,
        "ingredients": recipe.ingredients,
        "results": recipe.results,
        "energy_required": recipe.energy_required,
    }

    return recipe_data


# Global docs - not scoped to a server
@mcp.resource(
    f"{HOST}" + "://api/docs/{method}",
    name="API documentation",
    mime_type="text/markdown",
)
async def get_all_api_docs(method: str):
    """Get all API docs"""

    execution_path = (
        Path(os.path.dirname(os.path.realpath(__file__))).parent
        / Path("env")
        / Path("src")
    )
    generator = SystemPromptGenerator(str(execution_path))
    return generator.manual(method)


# Global api schema - not scoped to a server
@mcp.resource(f"{HOST}://api/schema", name="API schema", mime_type="text/plain")
async def get_all_api_schema():
    """Get all API docs"""

    execution_path = (
        Path(os.path.dirname(os.path.realpath(__file__))).parent
        / Path("env")
        / Path("src")
    )
    generator = SystemPromptGenerator(str(execution_path))
    schema = (
        generator.schema() + "\n\n" + generator.types() + "\n\n" + generator.entities()
    )
    return schema.replace("env.src.", "")
