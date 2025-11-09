import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from fle.env import FactorioInstance
from fle.commons.cluster_ips import get_local_container_ips
from fle.env.gym_env.registry import list_available_environments

from fle.env.protocols._mcp.models import FactorioServer, Recipe, ResourcePatch
from fle.env.protocols._mcp.repository import FactorioMCPRepository
import gym


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

        try:
            env_ids = list_available_environments()
            # print(f"DEBUG: Available environment IDs: {env_ids}")
            # print(f"DEBUG: Number of environments found: {len(env_ids)}")

            if not env_ids:
                raise Exception("No environments found")

            for id in env_ids:
                if "open" in id:
                    print(f"DEBUG: Using open environment: {id}")
                    self.gym_env = gym.make(id, run_idx=0)
                    self.gym_env.reset()
                    return

            # print(f"DEBUG: No open environment found, using first available: {env_ids[0]}")
            self.gym_env = gym.make(env_ids[0], run_idx=0)

            # program = await self.create_program_from_policy(
            #     policy=policy,
            #     agent_idx=agent_idx,
            #     reward=reward,
            #     response=obs_dict["raw_text"],
            #     error_occurred=info["error_occurred"],
            #     game_state=output_game_state
            # )
            #
        except IndexError as e:
            print(f"IndexError in __init__: {e}")
            print(
                f"env_ids length: {len(env_ids) if 'env_ids' in locals() else 'Not available'}"
            )
            print("Falling back to steel_plate_throughput environment")
            self.gym_env = gym.make("steel_plate_throughput", run_idx=0)
        except Exception as e:
            print(f"Error in __init__: {e}")
            print(f"Error type: {type(e)}")
            print("Falling back to steel_plate_throughput environment")
            self.gym_env = gym.make("steel_plate_throughput", run_idx=0)

        self.gym_env.reset()

    def create_factorio_instance(self, instance_id: int) -> FactorioInstance:
        """Create a single Factorio instance"""
        try:
            ips, udp_ports, tcp_ports = get_local_container_ips()

            if instance_id >= len(ips):
                raise IndexError(
                    f"instance_id {instance_id} out of range for ips list of length {len(ips)}"
                )
            if instance_id >= len(tcp_ports):
                raise IndexError(
                    f"instance_id {instance_id} out of range for tcp_ports list of length {len(tcp_ports)}"
                )

            instance = FactorioInstance(
                address=ips[instance_id],
                tcp_port=tcp_ports[instance_id],
                bounding_box=200,
                fast=True,
                cache_scripts=True,
                inventory={
                    "stone-furnace": 1,
                    "burner-mining-drill": 1,
                    "wood": 5,
                    "iron-plate": 8,
                },
                all_technologies_researched=False,
            )
            # Ensure agent characters exist (removed one-time associate command)
            # Check if agent characters exist, if not create them
            char_check = instance.rcon_client.send_command(
                "/c rcon.print(global.agent_characters and #global.agent_characters or 0)"
            )

            if int(char_check) == 0:
                instance.first_namespace._create_agent_characters(1)

            instance.set_speed(10)
            return instance
        except IndexError as e:
            print(f"IndexError in create_factorio_instance: {e}")
            try:
                print(f"Available IPs: {ips}")
                print(f"Available TCP ports: {tcp_ports}")
            except NameError:
                print("ERROR: Could not retrieve container IPs/ports")
            raise e
        except Exception as e:
            print(f"Error creating Factorio instance: {e}")
            print(f"Error type: {type(e)}")
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
        except Exception as e:
            print(f"Error connecting to Factorio server: {e}")
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

        # Navigate from fle/env/protocols/_mcp/state.py to project root
        recipes_path = (
            Path(__file__).parent.parent.parent.parent.parent / "data" / "recipes" / "recipes.jsonl"
        )

        if not recipes_path.exists():
            # If file doesn't exist, log a warning and return empty dict
            print(f"Warning: Recipes file not found at {recipes_path}")
            print("To generate recipes.jsonl, run: cd data/recipes && python main.py")
            self.recipes_loaded = True
            return {}

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
