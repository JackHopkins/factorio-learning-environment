import asyncio
import logging
from threading import Lock
from typing import List, Optional

from a2a.types import AgentCard

from fle.env import FactorioInstance

from fle.env.a2a_namespace import A2AFactorioNamespace
from fle.env.protocols.a2a.server import ServerManager


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
    async def create(
        cls, *args, agent_cards: Optional[List[AgentCard]] = None, **kwargs
    ):
        """Factory method to create and initialize an A2AFactorioInstance.

        :param agent_cards: Optional list of AgentCard objects for each agent
        :param args: Additional arguments passed to FactorioInstance
        :param kwargs: Additional keyword arguments passed to FactorioInstance

        Usage:
            instance = await A2AFactorioInstance.create(address='localhost', agent_cards=[card1, card2], ...)
        """
        cls._initialized = True
        try:
            instance = cls(*args, **kwargs)
            cls._ensure_server_running()
            await instance.async_initialise(agent_cards=agent_cards)
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
                if hasattr(namespace, "a2a_handler") and namespace.a2a_handler:
                    await namespace.a2a_handler.__aexit__(None, None, None)
            except Exception as e:
                logging.error(
                    f"Instance {self.id}: Error during a2a_handler.__aexit__ for {getattr(namespace.a2a_handler, 'agent_id', f'agent_in_namespace_{i}')}: {e}"
                )

    async def async_initialise(self, agent_cards: Optional[List[AgentCard]] = None):
        """Initialize the instance with A2A support"""
        if self._is_initialised:
            logging.info(f"Instance {self.id}: Already initialised. Re-initialising.")
        logging.info(
            f"Instance {self.id}: Starting async_initialise (fast={self.fast})..."
        )

        # Ensure any previous A2A handlers are closed before potentially overwriting them
        await self._unregister_agents()
        super().initialise(fast=self.fast)
        # Setup A2A handlers for multi-agent using the namespace's async method
        server_url = self._ensure_server_running()
        for i in range(self.num_agents):
            try:
                agent_card = (
                    agent_cards[i] if agent_cards and i < len(agent_cards) else None
                )
                await self.namespaces[i].async_setup_default_a2a_handler(
                    server_url, agent_card
                )
            except Exception as e:
                agent_identifier = self.namespaces[i].agent_id
                logging.error(
                    f"Instance {self.id}: Error during namespace A2A setup for agent {agent_identifier}: {e}",
                    exc_info=True,
                )

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
                logging.error(
                    f"Instance {self.id}: Error during A2A handler cleanup: {e}"
                )

        # Call parent cleanup
        super().cleanup()
