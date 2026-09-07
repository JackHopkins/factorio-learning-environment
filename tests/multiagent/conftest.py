import asyncio
import threading

import pytest

from fle.env.a2a_instance import A2AFactorioInstance
from fle.env.protocols.a2a.server import ServerManager


@pytest.fixture
def multi_instance(instance, unused_tcp_port):
    """Create a two-agent instance with an isolated local A2A server."""
    previous_manager = A2AFactorioInstance._server_manager
    manager = ServerManager(port=unused_tcp_port)
    A2AFactorioInstance._server_manager = manager
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    multi = asyncio.run_coroutine_threadsafe(
        A2AFactorioInstance.create(
            address="localhost",
            bounding_box=200,
            tcp_port=instance.tcp_port,
            cache_scripts=True,
            fast=True,
            inventory=dict(instance.initial_inventory),
            num_agents=2,
        ),
        loop,
    ).result()

    try:
        yield multi
    finally:
        asyncio.run_coroutine_threadsafe(multi._unregister_agents(), loop).result()
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join()
        loop.close()
        manager.stop_server()
        A2AFactorioInstance._server_manager = previous_manager
