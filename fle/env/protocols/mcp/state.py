import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from fle.env import FactorioInstance
from fle.commons.cluster_ips import get_local_container_ips

from fle.commons.models import FactorioServer, Recipe, ResourcePatch
from fle.env.protocols.mcp.repository import FactorioMCPRepository


class FactorioMCPState:
    """Manages the state of the Factorio MCP server"""

    def __init__(self):
        self.available_servers: Dict[int, FactorioServer] = {}  # instance_id -> server
        self.active_server: Optional[FactorioInstance] = None
        self.server_entities: Dict[
            int, Dict[str, Any]
        ] = {}  # instance_id -> {entity_id -> entity}
        self.server_resources: Dict[
            int, Dict[str, ResourcePatch]
        ] = {}  # instance_id -> {resource_id -> resource}
        self.recipes: Dict[str, Recipe] = {}  # Global recipes
        self.recipes_loaded = (
            False  # Flag to track if recipes have been loaded from file
        )
        self.checkpoints: Dict[
            int, Dict[str, str]
        ] = {}  # instance_id -> {checkpoint_name -> save file path}
        self.current_task: Optional[str] = None
        self.last_entity_update = 0
        self.vcs_repos: Dict[
            int, "FactorioMCPRepository"
        ] = {}  # instance_id -> VCS repo

    def create_factorio_instance(self, instance_id: int) -> FactorioInstance:
        """Create a single Factorio instance"""
        ips, udp_ports, tcp_ports = get_local_container_ips()
        try:
            instance = FactorioInstance(
                address=ips[instance_id],
                tcp_port=tcp_ports[instance_id],
                bounding_box=200,
                fast=True,
                cache_scripts=True,
                inventory={},
                all_technologies_researched=True,
            )
            instance.speed(10)
            return instance
        except Exception as e:
            print(f"Error creating Factorio instance: {e}")
            raise e

    async def scan_for_servers(self, ctx=None) -> List[FactorioServer]:
        """Scan for running Factorio servers"""
        try:
            ips, udp_ports, tcp_ports = get_local_container_ips()
            # print("scanning for servers")
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
                    if (
                        not server.is_active
                    ):  # or time.time() - server.last_checked > 60:
                        try:
                            self.create_factorio_instance(i)
                            server.is_active = True
                        except Exception as e:
                            server.is_active = False
                            server.system_response = str(e)
                            print(str(e))

                    new_servers[instance_id] = server
                else:
                    # Create new server entry
                    server = FactorioServer(
                        address=ips[i],
                        tcp_port=int(tcp_ports[i]),
                        instance_id=instance_id,
                        name=f"Factorio Server {i + 1}",
                        last_checked=time.time(),
                    )
                    # Try to verify if it's active
                    try:
                        self.create_factorio_instance(i)
                        server.is_active = True
                    except Exception as e:
                        server.is_active = False
                        server.system_response = str(e)
                        # print(e)

                    new_servers[instance_id] = server

                    if instance_id not in self.checkpoints:
                        self.checkpoints[instance_id] = {}

            self.available_servers = new_servers
            return list(self.available_servers.values())

        except Exception as e:
            raise e

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

            self.active_server = instance

            # Initial data fetch
            await self.refresh_game_data(instance_id)

            # Initialize recipes (global)
            if not self.recipes:
                self.recipes = self.load_recipes_from_file()

            # Initialize VCS repository for this instance if it doesn't exist
            if instance_id not in self.vcs_repos:
                print("Initializing repo")
                self.vcs_repos[instance_id] = FactorioMCPRepository(instance)

            return True
        except Exception:
            # print(f"Error connecting to Factorio server: {e}")
            return False

    def get_vcs(self):
        """Get the VCS repository for the active server"""
        if not self.active_server:
            return None

        instance_id = self.active_server.tcp_port
        if instance_id not in self.vcs_repos:
            self.vcs_repos[instance_id] = FactorioMCPRepository(self.active_server)

        return self.vcs_repos[instance_id]

    async def refresh_game_data(self, instance_id: int):
        """Refresh game data for a specific server instance"""
        if instance_id not in self.available_servers:
            return False

        self.last_entity_update = time.time()
        return True

    def load_recipes_from_file(self) -> Dict[str, Recipe]:
        """Load recipes from the jsonl file"""
        if self.recipes_loaded:
            return self.recipes

        recipes_path = (
            Path(__file__).parent.parent / "data" / "recipes" / "recipes.jsonl"
        )

        if not recipes_path.exists():
            # Fall back to absolute path if relative path fails
            recipes_path = Path(
                "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/data/recipes/recipes.jsonl"
            )

        try:
            recipes = {}
            with open(recipes_path, "r") as f:
                for line in f:
                    if line.strip():
                        try:
                            recipe_data = json.loads(line)
                            # Extract top-level ingredients and results
                            ingredients = recipe_data.get("ingredients", [])
                            # For simplicity, we'll use just the name and amount from ingredients
                            simplified_ingredients = []
                            for ingredient in ingredients:
                                simplified_ingredients.append(
                                    {
                                        "name": ingredient.get("name", ""),
                                        "amount": ingredient.get("amount", 1),
                                    }
                                )

                            # Most recipes don't have a results field in the JSONL, so we'll create one
                            results = [
                                {"name": recipe_data.get("name", ""), "amount": 1}
                            ]

                            recipes[recipe_data["name"]] = Recipe(
                                name=recipe_data["name"],
                                ingredients=simplified_ingredients,
                                results=results,
                                energy_required=1.0,  # Default value as it's not in the JSONL
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
            raise e
