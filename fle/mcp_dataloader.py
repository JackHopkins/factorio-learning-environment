#!/usr/bin/env python3
"""
Read-only MCP Client for Factorio Overlay using FastMCP
Connects to an existing MCP server and reads data without controlling it
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from queue import Queue
import threading

from fastmcp import Client

logger = logging.getLogger(__name__)


class MCPReadOnlyClient:
    """Read-only client that connects to an existing MCP server using FastMCP"""

    def __init__(
        self,
        mcp_server: str = "python -m fle.env.protocols._mcp",
        update_queue: Optional[Queue] = None,
    ):
        """
        Initialize MCP read-only client

        Args:
            mcp_server: Command string or URL to connect to MCP server
            update_queue: Queue for sending updates to the UI
        """
        self.mcp_server = mcp_server
        self.update_queue = update_queue
        self.client: Optional[Client] = None
        self.polling_active = False

    async def connect(self):
        """Connect to the existing MCP server"""
        try:
            # Use stdio transport explicitly
            # transport = StdioTransport(
            #     command=self.mcp_server[0],
            #     args=self.mcp_server[1:] if len(self.mcp_server) > 1 else []
            # )
            # async with Client("http://localhost:8000/sse") as client:
            #   tools = await client.list_tools()
            #   pass
            # self.client = Client(transport)
            from fastmcp.mcp_config import StdioMCPServer

            server = StdioMCPServer(
                command="/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.venv/bin/python",
                args=["-m", "fle.env.protocols._mcp"],
                env={
                    "PYTHONPATH": "/Users/jackhopkins/PycharmProjects/PaperclipMaximiser"
                },
                transport="stdio",
            )
            self.client = Client({"mcpServers": {"fle": server.__dict__}})

            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the MCP server"""
        self.polling_active = False

        if self.client:
            try:
                await self.client.close()  # .__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error disconnecting from MCP server: {e}")
            self.client = None

    async def read_resource(self, ctx, uri: str) -> Any:
        """Read a resource from the MCP server"""
        if not self.client:
            raise Exception("Not connected to MCP server")

        try:
            result = await ctx.read_resource(uri)

            # Parse the result based on content type
            if result and result:
                content = result[0]
                if hasattr(content, "text"):
                    try:
                        # Try to parse as JSON
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        # Return as plain text if not JSON
                        return content.text
                elif (
                    hasattr(content, "mimeType")
                    and content.mimeType == "application/json"
                ):
                    return json.loads(content.text)
                return content
            return None

        except Exception as e:
            logger.debug(f"Error reading resource {uri}: {e}")
            return None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool on the MCP server"""
        if not self.client:
            raise Exception("Not connected to MCP server")

        try:
            result = await self.client.call_tool(tool_name, arguments or {})
            return result
        except Exception as e:
            logger.debug(f"Error calling tool {tool_name}: {e}")
            return None

    async def poll_game_state(self):
        """Poll the MCP server for game state updates"""
        poll_count = 0

        async with self.client as ctx:
            while self.polling_active:
                try:
                    poll_count += 1
                    state = {}

                    # Read inventory
                    inventory = await self.read_resource(ctx, "fle://inventory")
                    if inventory:
                        state["inventory"] = inventory

                    # Read position
                    position = await self.read_resource(ctx, "fle://position")
                    if position:
                        state["position"] = position

                    # Read warnings
                    warnings = await self.read_resource(ctx, "fle://warnings")
                    if warnings:
                        state["warnings"] = warnings

                    # Read entities around player position
                    if position and isinstance(position, dict):
                        x = position.get("x", 0)
                        y = position.get("y", 0)
                        entities_uri = f"fle://entities/{x}/{y}/100"
                        entities = await self.read_resource(ctx, entities_uri)
                        if entities:
                            state["entities"] = entities
                            state["entities_count"] = (
                                len(entities) if isinstance(entities, list) else 0
                            )

                    # Read status
                    status = await self.read_resource(ctx, "fle://status")
                    if status:
                        state["status"] = status

                    metrics = await self.read_resource(ctx, "fle://metrics")
                    if metrics:
                        state["metrics"] = metrics

                    # Try to get rendered image
                    if position and isinstance(position, dict):
                        try:
                            # Call the render tool
                            result = await self.call_tool(
                                "render",
                                {
                                    "center_x": position.get("x", 0),
                                    "center_y": position.get("y", 0),
                                },
                            )

                            # Extract image from result
                            if result and hasattr(result, "content"):
                                for content in result.content:
                                    if (
                                        hasattr(content, "type")
                                        and content.type == "image"
                                    ):
                                        if hasattr(content, "data"):
                                            state["image"] = (
                                                f"data:image/png;base64,{content.data}"
                                            )
                                            logger.debug("Got rendered image")
                                            break
                        except Exception as e:
                            logger.debug(f"Could not get render: {e}")

                    # Send update to queue if we have data
                    if state and self.update_queue:
                        state["type"] = "state_update"
                        state["timestamp"] = asyncio.get_event_loop().time()
                        state["poll_count"] = poll_count
                        self.update_queue.put(state)
                        logger.debug(
                            f"Poll #{poll_count}: sent update with keys: {list(state.keys())}"
                        )

                except Exception as e:
                    logger.error(f"Error during polling (poll #{poll_count}): {e}")
                    if self.update_queue:
                        self.update_queue.put({"type": "error", "message": str(e)})

                # Wait before next poll
                await asyncio.sleep(3.0)

        logger.info(f"Polling stopped after {poll_count} polls")

    async def start_polling(self):
        """Start polling for game state updates"""
        self.polling_active = True
        await self.poll_game_state()


class MCPDataBridge:
    """Bridge between MCP server and overlay UI using FastMCP"""

    def __init__(
        self, update_queue: Queue, mcp_server: str = "python -m fle.env.protocols._mcp"
    ):
        """
        Initialize the MCP data bridge

        Args:
            update_queue: Queue for sending updates to the UI
            mcp_server: Server specification (command string, URL, or config)
        """
        self.update_queue = update_queue
        self.mcp_server = mcp_server
        self.client = None
        self.bridge_thread = None
        self.bridge_loop = None

    def start(self):
        """Start the MCP bridge in a separate thread"""
        self.bridge_thread = threading.Thread(target=self._run_bridge)
        self.bridge_thread.daemon = True
        self.bridge_thread.start()

        logger.info("MCP bridge thread started")

    def _run_bridge(self):
        """Run the bridge event loop"""
        self.bridge_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.bridge_loop)

        try:
            self.bridge_loop.run_until_complete(self._async_connect_and_poll())
        except Exception as e:
            logger.error(f"Bridge error: {e}")
            if self.update_queue:
                self.update_queue.put(
                    {"type": "error", "message": f"MCP Bridge error: {str(e)}"}
                )
        finally:
            logger.info("Bridge event loop ended")

    async def _async_connect_and_poll(self):
        """Connect to MCP and start polling"""
        self.client = None

        try:
            # Create MCP client
            self.client = MCPReadOnlyClient(
                mcp_server=self.mcp_server, update_queue=self.update_queue
            )

            # Connect to MCP server
            connected = await self.client.connect()
            if not connected:
                raise Exception("Failed to connect to MCP server")

            logger.info("MCP connection established via FastMCP")

            # Send init message to overlay
            self.update_queue.put(
                {
                    "type": "init",
                    "task": "MCP Monitoring Mode",
                    "message": "Connected to MCP server via FastMCP",
                }
            )

            # Start polling (blocks until polling_active becomes False)
            await self.client.start_polling()

        except Exception as e:
            logger.error(f"Error in async connect and poll: {e}")
            raise

        finally:
            # Ensure cleanup
            if self.client:
                await self.client.disconnect()
                logger.info("MCP client disconnected")

    def stop(self):
        """Stop the MCP bridge"""
        logger.info("Stopping MCP bridge")

        if self.client:
            self.client.polling_active = False

        # Give the loop time to finish
        if self.bridge_loop and self.bridge_loop.is_running():
            # Schedule the loop to stop
            self.bridge_loop.call_soon_threadsafe(self.bridge_loop.stop)

        if self.bridge_thread and self.bridge_thread.is_alive():
            # Wait for thread to complete
            self.bridge_thread.join(timeout=5)

        logger.info("MCP bridge stopped")
