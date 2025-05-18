import logging
import asyncio
from typing import Optional, List
from threading import Lock
from env.src.instance import FactorioInstance
from env.src.protocols.a2a.handler import A2AProtocolHandler
from env.src.protocols.a2a.server import ServerManager
from env.src.a2a_namespace import A2AFactorioNamespace

class A2AFactorioInstance(FactorioInstance):
    """A FactorioInstance with A2A (Agent-to-Agent) communication support."""
    
    namespace_class = A2AFactorioNamespace
    _server_manager = None
    _initialized = False
    _init_lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._initialized:
            raise RuntimeError(
                "Direct instantiation of A2AFactorioInstance is not allowed. "
                "Please use A2AFactorioInstance.create() instead."
            )
        return super().__new__(cls)

    @classmethod
    async def create(cls, *args, **kwargs):
        """Factory method to create and initialize an A2AFactorioInstance.
        
        Usage:
            instance = await A2AFactorioInstance.create(address='localhost', ...)
        """
        cls._initialized = True
        try:
            instance = cls(*args, **kwargs)
            cls._ensure_server_running()
            await instance.async_initialise()
            return instance
        finally:
            cls._initialized = False  # Reset for next creation, even if an error occurs

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.cleanup()
    

    @classmethod
    def _ensure_server_running(cls):
        """Ensure the A2A server is running"""
        if cls._server_manager is None:
            cls._server_manager = ServerManager()
        cls._server_manager.start_server()
        return cls._server_manager.server_url

    @classmethod
    def cleanup_server(cls):
        """Clean up the A2A server if it's running"""
        if cls._server_manager is not None:
            cls._server_manager.stop_server()
            cls._server_manager = None

    async def _unregister_agents(self):
        """Unregister all agents from the A2A server"""
        for i, namespace in enumerate(self.namespaces):
            try:
                if hasattr(namespace, 'a2a_handler') and namespace.a2a_handler:
                    await namespace.a2a_handler.__aexit__(None, None, None)
            except Exception as e:
                logging.error(f"Instance {self.id}: Error during a2a_handler.__aexit__ for {getattr(namespace.a2a_handler, 'agent_id', f'agent_in_namespace_{i}')}: {e}")

    async def async_initialise(self):
        """Initialize the instance with A2A support"""
        if self._is_initialised:
            logging.info(f"Instance {self.id}: Already initialised. Re-initialising.")
        logging.info(f"Instance {self.id}: Starting async_initialise (fast={self.fast})...")
        
        # Ensure any previous A2A handlers are closed before potentially overwriting them
        await self._unregister_agents()

        # Original initialise RCON commands (ensure these are run after connect)
        self.begin_transaction()
        self.add_command('/sc global.alerts = {}', raw=True)
        self.add_command('/sc global.elapsed_ticks = 0', raw=True)
        self.add_command('/sc global.fast = {}'.format('true' if self.fast else 'false'), raw=True)
        self.execute_transaction()
        
        # Load Lua scripts (ensure LuaScriptManager is ready)
        if self.peaceful: 
            self.lua_script_manager.load_init_into_game('enemies') 
        
        init_scripts = ['initialise', 'clear_entities', 'alerts', 'util', 'priority_queue', 
                        'connection_points', 'recipe_fluid_connection_mappings', 
                        'serialize', 'production_score', 'initialise_inventory']
        for script_name in init_scripts:
            self.lua_script_manager.load_init_into_game(script_name)

        inventories = [self.initial_inventory] * self.num_agents
        self._reset(inventories)
        self.first_namespace._clear_collision_boxes()

        # Create in-game characters for agents if there are any
        self._create_agent_game_characters()
        
        # Setup A2A handlers for multi-agent using the namespace's async method
        server_url = self._ensure_server_running()
        for i in range(self.num_agents):
            try:
                await self.namespaces[i].async_setup_default_a2a_handler(server_url)
            except Exception as e:
                agent_identifier = self.namespaces[i].agent_id 
                logging.error(f"Instance {self.id}: Error during namespace A2A setup for agent {agent_identifier}: {e}", exc_info=True)

        self._is_initialised = True
        logging.info(f"Instance {self.id}: async_initialise completed.")
        return self

    def cleanup(self):
        """Clean up instance resources including A2A handlers"""
        # Close A2A handlers
        if self._is_initialised:
            try:
                # Create a new event loop for cleanup
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                
                # Run the unregister function
                temp_loop.run_until_complete(self._unregister_agents())
                
                # Clean up the loop
                temp_loop.close()
            except Exception as e:
                logging.error(f"Instance {self.id}: Error during A2A handler cleanup: {e}")
        
        # Call parent cleanup
        super().cleanup()
