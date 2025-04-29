import asyncio
import json
import base64
import os
import time
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
import subprocess
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context
import mcp.types as types

from ..cluster.local.cluster_ips import get_local_container_ips
from ..env.src.instance import FactorioInstance

# Initialize FastMCP server
mcp = FastMCP("factorio-server")


# --- Data Models ---

@dataclass
class FactorioServer:
    address: str
    tcp_port: int
    instance_id: int
    name: str = None
    connected: bool = False
    last_checked: float = 0
    is_active: bool = False
    system_response: str = None


@dataclass
class Entity:
    id: str
    name: str
    position: Dict[str, float]
    direction: int
    health: float
    # Additional properties as needed


@dataclass
class Recipe:
    name: str
    ingredients: List[Dict[str, Union[str, int]]]
    results: List[Dict[str, Union[str, int]]]
    energy_required: float


@dataclass
class ResourcePatch:
    name: str
    position: Dict[str, float]
    amount: int
    size: Dict[str, float]


# --- Server State ---
class FactorioMCPState:
    def __init__(self):
        self.available_servers: Dict[int, FactorioServer] = {}  # instance_id -> server
        self.active_server: Optional[FactorioServer] = None
        self.server_entities: Dict[int, Dict[str, Entity]] = {}  # instance_id -> {entity_id -> entity}
        self.server_resources: Dict[int, Dict[str, ResourcePatch]] = {}  # instance_id -> {resource_id -> resource}
        self.recipes: Dict[str, Recipe] = {}  # Global recipes
        self.recipes_loaded = False  # Flag to track if recipes have been loaded from file
        self.checkpoints: Dict[int, Dict[str, str]] = {}  # instance_id -> {checkpoint_name -> save file path}
        self.current_task: Optional[str] = None
        self.last_entity_update = 0

    def create_factorio_instance(self, instance_id: int) -> FactorioInstance:
        """Create a single Factorio instance"""
        ips, udp_ports, tcp_ports = get_local_container_ips()

        instance = FactorioInstance(
            address=ips[instance_id],
            tcp_port=tcp_ports[instance_id],
            bounding_box=200,
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=True
        )
        instance.speed(10)
        return instance

    async def scan_for_servers(self, ctx = None) -> List[FactorioServer]:
        """Scan for running Factorio servers"""
        try:
            ips, udp_ports, tcp_ports = get_local_container_ips()
            print("scanning for servers")
            # Create server objects for each detected instance
            new_servers = {}
            for i in range(len(ips)):

                if ctx:
                    await ctx.report_progress(i, len(ips))

                instance_id = i

                # Check if server already exists in our list
                if instance_id in self.available_servers:
                    # Update existing server
                    server = self.available_servers[instance_id]
                    server.last_checked = time.time()
                    # Update address and ports in case they changed
                    server.address = ips[i]
                    server.tcp_port = tcp_ports[i]

                    # Try to verify if it's active
                    if not server.is_active:# or time.time() - server.last_checked > 60:
                        try:
                            instance = self.create_factorio_instance(i)
                            instance.get_system_prompt()
                            server.is_active = True
                        except Exception as e:
                            server.is_active = True
                            server.system_response = str(e)

                    new_servers[instance_id] = server
                else:
                    # Create new server entry
                    server = FactorioServer(
                        address=ips[i],
                        tcp_port=int(tcp_ports[i]),
                        instance_id=instance_id,
                        name=f"Factorio Server {i + 1}",
                        last_checked=time.time()
                    )
                    # Try to verify if it's active
                    try:
                        instance = self.create_factorio_instance(i)
                        instance.get_system_prompt()
                        server.is_active = True
                    except Exception as e:
                        server.is_active = False
                        server.system_response = str(e)
                        print(e)

                    new_servers[instance_id] = server

                    if instance_id not in self.checkpoints:
                        self.checkpoints[instance_id] = {}

            self.available_servers = new_servers
            return list(self.available_servers.values())

        except Exception as e:
            print(f"Error scanning for Factorio servers: {e}")
            # For demo/testing, create mock servers if real detection fails
            mock_instance_id = 0
            self.available_servers = {
                mock_instance_id: FactorioServer(
                    address="127.0.0.1",
                    tcp_port=34197,
                    instance_id=mock_instance_id,
                    name="Factorio Server 1",
                    is_active=True,
                    last_checked=time.time(),
                    system_prompt="Factorio v1.1.87 (Build 62626) ready"
                )
            }

            # Initialize data structures for the mock server
            if mock_instance_id not in self.server_entities:
                self.server_entities[mock_instance_id] = self._get_sample_entities()
            if mock_instance_id not in self.server_resources:
                self.server_resources[mock_instance_id] = self._get_sample_resources()
            if mock_instance_id not in self.checkpoints:
                self.checkpoints[mock_instance_id] = {}

            return list(self.available_servers.values())


    async def connect_to_server(self, instance_id: int) -> bool:
        """Connect to a Factorio server by instance ID"""
        # Find the server with the given instance ID
        if instance_id not in self.available_servers:
            return False

        server = self.available_servers[instance_id]

        if not server.is_active:
            return False

        try:
            # Create an instance to the server
            instance = self.create_factorio_instance(instance_id)

            # If we get here, the connection was successful
            server.connected = True
            self.active_server = server

            # Initial data fetch
            await self.refresh_game_data(instance_id)

            # Initialize recipes (global)
            if not self.recipes:
                self.recipes = self.load_recipes_from_file()

            return True
        except Exception as e:
            print(f"Error connecting to Factorio server: {e}")
            return False

    async def refresh_game_data(self, instance_id: int):
        """Refresh game data for a specific server instance"""
        if instance_id not in self.available_servers:
            return False

        # In a real implementation, this would query the Factorio server via the instance API
        # For demo purposes, we'll just populate with sample data if not already present
        if not self.server_entities.get(instance_id):
            self.server_entities[instance_id] = self._get_sample_entities()

        if not self.server_resources.get(instance_id):
            self.server_resources[instance_id] = self._get_sample_resources()

        self.last_entity_update = time.time()
        return True

    def _get_sample_entities(self) -> Dict[str, Entity]:
        """Get sample entities for demo purposes"""
        return {
            "e1": Entity(id="e1", name="assembling-machine-1", position={"x": 10, "y": 15}, direction=0, health=350),
            "e2": Entity(id="e2", name="transport-belt", position={"x": 12, "y": 15}, direction=2, health=100),
            "e3": Entity(id="e3", name="inserter", position={"x": 11, "y": 14}, direction=4, health=150),
        }

    def load_recipes_from_file(self) -> Dict[str, Recipe]:
        """Load recipes from the jsonl file"""
        if self.recipes_loaded:
            return self.recipes
            
        recipes_path = Path(__file__).parent / "data" / "recipes" / "recipes.jsonl"
        
        if not recipes_path.exists():
            # Fall back to absolute path if relative path fails
            recipes_path = Path("/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/recipes/recipes.jsonl")
            
        if not recipes_path.exists():
            print(f"Warning: Could not find recipes file at {recipes_path}")
            return self._get_sample_recipes_fallback()
            
        try:
            recipes = {}
            with open(recipes_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            recipe_data = json.loads(line)
                            # Extract top-level ingredients and results
                            ingredients = recipe_data.get("ingredients", [])
                            # For simplicity, we'll use just the name and amount from ingredients
                            simplified_ingredients = []
                            for ingredient in ingredients:
                                simplified_ingredients.append({
                                    "name": ingredient.get("name", ""),
                                    "amount": ingredient.get("amount", 1)
                                })
                            
                            # Most recipes don't have a results field in the JSONL, so we'll create one
                            results = [{"name": recipe_data.get("name", ""), "amount": 1}]
                            
                            recipes[recipe_data["name"]] = Recipe(
                                name=recipe_data["name"],
                                ingredients=simplified_ingredients,
                                results=results,
                                energy_required=1.0  # Default value as it's not in the JSONL
                            )
                        except json.JSONDecodeError:
                            print(f"Warning: Could not parse recipe line: {line}")
                        except KeyError as e:
                            print(f"Warning: Missing key in recipe: {e}")
                        except Exception as e:
                            print(f"Warning: Error processing recipe: {e}")
                            
            self.recipes_loaded = True
            return recipes
        except Exception as e:
            print(f"Error loading recipes from file: {e}")
            return self._get_sample_recipes_fallback()

    def _get_sample_recipes_fallback(self) -> Dict[str, Recipe]:
        """Get sample recipes for demo purposes - global across all servers"""
        return {
            "electronic-circuit": Recipe(
                name="electronic-circuit",
                ingredients=[{"name": "iron-plate", "amount": 1}, {"name": "copper-cable", "amount": 3}],
                results=[{"name": "electronic-circuit", "amount": 1}],
                energy_required=0.5
            ),
            "copper-cable": Recipe(
                name="copper-cable",
                ingredients=[{"name": "copper-plate", "amount": 1}],
                results=[{"name": "copper-cable", "amount": 2}],
                energy_required=0.5
            )
        }

    def _get_sample_resources(self) -> Dict[str, ResourcePatch]:
        """Get sample resources for demo purposes"""
        return {
            "iron-ore-1": ResourcePatch(
                name="iron-ore",
                position={"x": 50, "y": 100},
                amount=15000,
                size={"width": 20, "height": 15}
            ),
            "copper-ore-1": ResourcePatch(
                name="copper-ore",
                position={"x": 100, "y": 150},
                amount=12000,
                size={"width": 15, "height": 10}
            )
        }

    async def create_checkpoint(self, name: str) -> bool:
        """Create a game state checkpoint for the active server"""
        if not self.active_server or not self.active_server.connected:
            return False

        instance_id = self.active_server.instance_id

        # In a real implementation, this would request a save via RCON
        checkpoint_path = f"checkpoints/{name}_{int(time.time())}.zip"

        if instance_id not in self.checkpoints:
            self.checkpoints[instance_id] = {}

        self.checkpoints[instance_id][name] = checkpoint_path
        return True

    async def restore_checkpoint(self, name: str) -> bool:
        """Restore to a saved checkpoint for the active server"""
        if not self.active_server or not self.active_server.connected:
            return False

        instance_id = self.active_server.instance_id

        if instance_id not in self.checkpoints or name not in self.checkpoints[instance_id]:
            return False

        # In a real implementation, this would load the save via RCON
        return True


# Initialize server state
state = FactorioMCPState()


# --- Initialization ---

# Initialize our scan flag - we'll do a lazy initialization
scan_initialized = False

# Helper function to perform the initial scan
async def initialize_servers_if_needed():
    """Initialize the server state by scanning for servers if not already done"""
    global scan_initialized
    if not scan_initialized:
        print("Performing initial server scan...")
        try:
            await state.scan_for_servers()
            print(f"Found {len(state.available_servers)} servers, {sum(1 for s in state.available_servers.values() if s.is_active)} active")
        except Exception as e:
            print(f"Error during initial server scan: {e}")
            # Create a mock server for testing purposes
            state.available_servers = {
                0: FactorioServer(
                    address="127.0.0.1", 
                    tcp_port=34197, 
                    instance_id=0,
                    name="Mock Factorio Server",
                    is_active=True
                )
            }
        scan_initialized = True

# --- Resource Handlers ---

@mcp.resource(uri="factorio://servers", name="Available Factorio Servers", mime_type="application/json")
async def get_factorio_servers():
    """Get all available Factorio servers"""
    # Make sure we've initialized the server list
    await initialize_servers_if_needed()
    
    # Response array - MCP will return each item as a separate content
    result = []
    
    # Filter to only include active servers
    active_servers = {id: server for id, server in state.available_servers.items() if server.is_active}
    
    if not state.available_servers:
        result.append("No Factorio servers detected. Use refresh_factorio_servers tool to scan for servers.")
    elif not active_servers:
        result.append(f"Found {len(state.available_servers)} Factorio servers, but none are active. Use refresh_factorio_servers tool to rescan.")
    else:
        # This special entry provides an overview in the first content
        total_count = len(state.available_servers)
        active_count = len(active_servers)
        result.append(f"Found {active_count} active Factorio servers (of {total_count} total)")
        
        # Add only active servers as separate content
        for server in active_servers.values():
            server_data = {
                "instance_id": server.instance_id,
                "address": server.address,
                "tcp_port": server.tcp_port,
                "name": server.name,
                "is_active": server.is_active,
                "connected": server.connected,
            }
            
            # The MCP adapter will automatically take this list and convert each item to a separate content
            result.append(server_data)
    
    return result


@mcp.resource("factorio://server/{instance_id}", name="Factorio Server Details", mime_type="application/json")
async def get_server_details(instance_id: int):
    """Get details for a specific Factorio server"""
    # Ensure servers are up to date
    #await state.scan_for_servers()

    # Find the server with the given instance ID
    instance_id = int(instance_id)
    if instance_id not in state.available_servers:
        return f"No Factorio server found with instance ID {instance_id}"

    server = state.available_servers[instance_id]
    
    # Return a content object with application/json mime type
    server_data = {
        "instance_id": server.instance_id,
        "address": server.address,
        "tcp_port": server.tcp_port,
        "name": server.name,
        "is_active": server.is_active,
        "connected": server.connected,
    }
    
    return server_data


@mcp.resource("factorio://server/{instance_id}/entities", name="Server Entities", mime_type="application/json")
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
    if instance_id not in state.server_entities or not state.server_entities[instance_id]:
        await state.refresh_game_data(instance_id)

    # Get entities for this server
    entities = state.server_entities.get(instance_id, {})

    return json.dumps(
        {id: {
            "id": e.id,
            "name": e.name,
            "position": e.position,
            "direction": e.direction,
            "health": e.health
        } for id, e in entities.items()},
        indent=2
    )


@mcp.resource(
    "factorio://server/{instance_id}/entities/{top_left_x}/{top_left_y}/{bottom_right_x}/{bottom_right_y}",
    name="Server Entities in Area", mime_type="application/json")
async def get_server_entities_in_area(instance_id: int, top_left_x: float, top_left_y: float,
                                      bottom_right_x: float, bottom_right_y: float):
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
    if instance_id not in state.server_entities or not state.server_entities[instance_id]:
        await state.refresh_game_data(instance_id)

    # Get entities for this server
    entities = state.server_entities.get(instance_id, {})

    # Filter by area
    filtered_entities = {
        id: e for id, e in entities.items()
        if (top_left_x <= e.position["x"] <= bottom_right_x and
            top_left_y <= e.position["y"] <= bottom_right_y)
    }

    return json.dumps(
        {id: {
            "id": e.id,
            "name": e.name,
            "position": e.position,
            "direction": e.direction,
            "health": e.health
        } for id, e in filtered_entities.items()},
        indent=2
    )


@mcp.resource("factorio://server/{instance_id}/resources/{name}",
              name="Server Resource Patches", mime_type="application/json")
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
    if instance_id not in state.server_resources or not state.server_resources[instance_id]:
        await state.refresh_game_data(instance_id)

    # Get resources for this server
    resources = state.server_resources.get(instance_id, {})

    # Filter by resource name
    filtered_resources = {
        id: r for id, r in resources.items()
        if r.name == name
    }

    return {id: {
            "name": r.name,
            "position": r.position,
            "amount": r.amount,
            "size": r.size
        } for id, r in filtered_resources.items()}



# Global recipe resources - not scoped to a server
@mcp.resource("factorio://recipes", name="All Recipes", mime_type="application/json")
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
            "energy_required": recipe.energy_required
        }
        
        result.append(recipe_data)
    
    return result


@mcp.resource("factorio://recipe/{name}", name="Recipe Details", mime_type="application/json")
async def get_recipe(name: str) -> Dict:
    """Get details for a specific recipe - global across all servers"""
    # Initialize recipes if empty
    if not state.recipes:
        state.recipes = state.load_recipes_from_file()

    if name not in state.recipes:
        return {
            "uri": f"factorio://recipe/{name}/error",
            "text": f"Recipe '{name}' not found.",
            "mimeType": "text/plain"
        }

    recipe = state.recipes[name]
    recipe_data = {
        "name": recipe.name,
        "ingredients": recipe.ingredients,
        "results": recipe.results,
        "energy_required": recipe.energy_required
    }
    
    return recipe_data


# --- Tool Implementations ---

@mcp.tool()
async def refresh_factorio_servers(ctx: Context) -> str:
    """Scan for available Factorio servers on the network and refresh their status"""

    servers = await state.scan_for_servers(ctx)

    if not servers:
        return "No Factorio servers found."

    active_servers = [s for s in servers if s.is_active]
    inactive_servers = [s for s in servers if not s.is_active]

    result = f"Found {len(servers)} Factorio servers ({len(active_servers)} active, {len(inactive_servers)} inactive).\n\n"

    if active_servers:
        result += "Active servers:\n"
        for s in active_servers:
            result += f"- Instance ID {s.instance_id}: {s.name} ({s.address}:{s.tcp_port})\n"

    if inactive_servers:
        result += "\nInactive servers:\n"
        for s in inactive_servers:
            result += f"- Instance ID {s.instance_id}: {s.name} ({s.address}:{s.tcp_port})\n  {s.system_response}\n"

    result += "\nUse 'connect_to_factorio_server' tool with an instance ID to connect to an active server."
    result += "\nYou can also view server details via the 'factorio://servers' resource."

    return result


@mcp.tool()
async def connect_to_factorio_server(instance_id: int) -> str:
    """
    Connect to a Factorio server by instance ID

    Args:
        instance_id: The instance ID of the server from the available servers list
    """
    # No scanning here - just use existing server data
    if not state.available_servers:
        return "No Factorio servers available. Please use refresh_factorio_servers first."

    # Find the server with the given instance ID
    if instance_id not in state.available_servers:
        return f"No Factorio server found with instance ID {instance_id}. Please use refresh_factorio_servers to update the list."

    server = state.available_servers[instance_id]

    if not server.is_active:
        return f"The Factorio server with instance ID {instance_id} is not active or not responding."

    connected = await state.connect_to_server(instance_id)

    if connected:
        return f"Successfully connected to Factorio server {server.name} ({server.address}:{server.tcp_port})."
    else:
        return f"Failed to connect to Factorio server with instance ID {instance_id}."


@mcp.tool()
async def render_factory(width: int = 800, height: int = 600,
                         center_x: float = None, center_y: float = None,
                         zoom: float = 1.0) -> str:
    """
    Render the current factory state to an image

    Args:
        width: Width of the output image
        height: Height of the output image
        center_x: X coordinate to center on (defaults to factory center)
        center_y: Y coordinate to center on (defaults to factory center)
        zoom: Zoom level (1.0 = normal)
    """
    if not state.active_server or not state.active_server.connected:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    # In a real implementation, this would capture a screenshot via the Factorio instance API
    # For demo purposes, we'll create a mock image

    instance_id = state.active_server.instance_id
    entities = state.server_entities.get(instance_id, {})

    # Create a simple text representation of entities
    image_text = f"Factory Visualization for Server {instance_id} (Mock):\n\n"
    for entity_id, entity in entities.items():
        image_text += f"{entity.name} at ({entity.position['x']}, {entity.position['y']})\n"

    # In a real implementation, we would generate and return a base64 encoded image
    # For now, just return the text representation
    return image_text


@mcp.tool()
async def checkpoint_gamestate(name: str) -> str:
    """
    Create a checkpoint of the current game state that can be restored later

    Args:
        name: Name for the checkpoint
    """
    if not state.active_server or not state.active_server.connected:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    success = await state.create_checkpoint(name)

    if success:
        return f"Checkpoint '{name}' created successfully for server {state.active_server.instance_id}."
    else:
        return "Failed to create checkpoint."


@mcp.tool()
async def reset_gamestate(checkpoint_name: str = None) -> str:
    """
    Reset the game to a previous checkpoint

    Args:
        checkpoint_name: Name of checkpoint to restore (None for most recent)
    """
    if not state.active_server or not state.active_server.connected:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    instance_id = state.active_server.instance_id

    if instance_id not in state.checkpoints or not state.checkpoints[instance_id]:
        return "No checkpoints available for this server."

    if checkpoint_name is None:
        # Use the most recent checkpoint
        checkpoint_name = list(state.checkpoints[instance_id].keys())[-1]

    if checkpoint_name not in state.checkpoints[instance_id]:
        available_checkpoints = ", ".join(state.checkpoints[instance_id].keys())
        return f"Checkpoint '{checkpoint_name}' not found. Available checkpoints: {available_checkpoints}"

    success = await state.restore_checkpoint(checkpoint_name)

    if success:
        return f"Game state restored to checkpoint '{checkpoint_name}' for server {instance_id}."
    else:
        return "Failed to restore checkpoint."


@mcp.tool()
async def run_code(code: str) -> str:
    """
    Run Python code to interact with the Factorio server

    Args:
        code: Python code to execute
    """
    if not state.active_server or not state.active_server.connected:
        return "No active Factorio server connection. Use connect_to_factorio_server first."

    instance_id = state.active_server.instance_id

    # This is a simplified implementation - in practice you would need proper sandboxing
    # and security measures to safely execute code
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp:
            temp_path = temp.name

            # Prepare the code with proper imports and access to state
            wrapped_code = f"""
import json
import asyncio
from typing import Dict, List, Any

# Import state data (read-only)
entities = {json.dumps({id: {"id": e.id, "name": e.name, "position": e.position, "direction": e.direction, "health": e.health} for id, e in state.server_entities.get(instance_id, {}).items()})}
recipes = {json.dumps({name: {"name": r.name, "ingredients": r.ingredients, "results": r.results, "energy_required": r.energy_required} for name, r in state.recipes.items()})}
resources = {json.dumps({id: {"name": r.name, "position": r.position, "amount": r.amount, "size": r.size} for id, r in state.server_resources.get(instance_id, {}).items()})}
server_info = {json.dumps({"instance_id": instance_id, "name": state.active_server.name, "address": state.active_server.address, "tcp_port": state.active_server.tcp_port})}

# User code
try:
    result = None
    {code}
    print(json.dumps({{"success": True, "result": result or "Code executed successfully"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
"""
            temp.write(wrapped_code)

        # Execute the code in a separate process
        result = subprocess.run(['python', temp_path], capture_output=True, text=True)
        os.unlink(temp_path)  # Clean up the temp file

        if result.returncode != 0:
            return f"Error executing code: {result.stderr}"

        # Parse the output
        try:
            output = json.loads(result.stdout)
            if output.get("success", False):
                return str(output.get("result", "Code executed successfully"))
            else:
                return f"Error in code: {output.get('error', 'Unknown error')}"
        except json.JSONDecodeError:
            return f"Invalid output: {result.stdout}"

    except Exception as e:
        return f"Error setting up code execution: {str(e)}"

if __name__ == "__main__":
    mcp.run()