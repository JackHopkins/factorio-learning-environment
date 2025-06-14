from typing import Dict, Any, Optional, List
import time
import uuid
import aiohttp
import asyncio
from pydantic import BaseModel
import requests
from a2a.types import Message, Part, TextPart, AgentCard, Role


class A2AMessage(BaseModel):
    """Enhanced message format supporting A2A protocol"""

    sender: str
    recipient: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = {}
    message_type: str = "text"
    timestamp: float = time.time()
    is_new: bool = True


class A2AProtocolHandler:
    def __init__(
        self,
        agent_id: str,
        server_url: str,
        agent_card: AgentCard,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        self.agent_id = agent_id
        # Ensure server_url ends with /a2a
        self.server_url = server_url.rstrip("/")
        if not self.server_url.endswith("/a2a"):
            self.server_url = f"{self.server_url}/a2a"
        self.agent_card = agent_card
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._is_registered = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._cleanup_lock = asyncio.Lock()

    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        await self.register()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._cleanup_lock:
            try:
                if self._is_registered:
                    try:
                        await self.unregister()
                    except Exception as e:
                        # Log but don't raise during cleanup
                        print(f"Warning: Error during unregister: {str(e)}")
                if self._session:
                    try:
                        await self._session.close()
                    except Exception as e:
                        print(f"Warning: Error closing session: {str(e)}")
                    finally:
                        self._session = None
            except Exception as e:
                print(f"Warning: Error during cleanup: {str(e)}")

    def _make_sync_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._is_registered:
            raise RuntimeError("Agent must be registered before making requests")

        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.server_url, json=request)

                if response.status_code == 404:
                    raise Exception(f"Endpoint not found: {self.server_url}")

                result = response.json()
                if "error" in result and result["error"] is not None:
                    raise Exception(f"A2A protocol error: {result['error']}")
                return result.get("result", {})

            except requests.RequestException:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay)

    async def _make_request(
        self, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self._session:
            raise RuntimeError(
                "Session not initialized. Use 'async with' context manager."
            )

        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }

        for attempt in range(self.max_retries):
            try:
                async with self._session.post(
                    self.server_url, json=request
                ) as response:
                    if response.status == 404:
                        raise Exception(f"Endpoint not found: {self.server_url}")

                    result = await response.json()
                    if "error" in result and result["error"] is not None:
                        raise Exception(f"A2A protocol error: {result['error']}")
                    return result.get("result", {})
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)

    async def register(self) -> None:
        """Register this agent with the A2A server"""
        try:
            await self._make_request(
                "register",
                {"agent_id": self.agent_id, "agent_card": self.agent_card.dict()},
            )
            self._is_registered = True
        except Exception as e:
            print(f"Warning: Error during register: {str(e)}")
            raise

    async def unregister(self) -> None:
        """Unregister this agent from the A2A server"""
        try:
            await self._make_request("unregister", {"agent_id": self.agent_id})
            self._is_registered = False
        except Exception as e:
            print(f"Warning: Error during unregister: {str(e)}")
            # Don't raise during unregister to ensure cleanup continues
            self._is_registered = False

    async def discover_agents(self) -> List[Dict[str, Any]]:
        """Discover other agents registered with the A2A server"""
        result = await self._make_request("discover", {})
        return result.get("agents", [])

    async def negotiate_capabilities(
        self, agent_id: str, capabilities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Negotiate capabilities with another agent"""
        result = await self._make_request(
            "negotiate", {"agent_id": agent_id, "capabilities": capabilities}
        )
        return result

    def send_message(self, message: Message) -> None:
        """Send a message to another agent through the A2A server"""
        self._make_sync_request(
            "send_message",
            {
                "sender_id": self.agent_id,
                "recipient_id": message.metadata.get("recipient"),
                "message": {
                    "messageId": message.messageId,
                    "role": str(message.role),
                    "parts": [
                        {"root": {"text": part.root.text}} for part in message.parts
                    ],
                    "metadata": message.metadata,
                },
            },
        )

    def get_messages(self) -> List[Message]:
        """Get messages sent to this agent"""
        result = self._make_sync_request("get_messages", {"agent_id": self.agent_id})
        messages = result.get("messages", [])
        return [
            Message(
                messageId=msg.get("messageId", str(uuid.uuid4())),
                role=Role.agent,  # Default to "agent" if not specified
                parts=[Part(root=TextPart(text=msg.get("content", "")))],
                metadata=msg.get("metadata", {}),
            )
            for msg in messages
        ]

    def load_messages(self, messages: List[Message]) -> None:
        """
        Load messages into the agent's message queue on the server.
        :param messages: List of Message objects to load
        """
        if not self._is_registered:
            raise Exception("Agent must be registered before loading messages")

        # Convert Message objects to server format
        server_messages = []
        for msg in messages:
            server_messages.append(
                {
                    "messageId": msg.messageId,
                    "role": str(msg.role),
                    "parts": [{"root": {"text": part.root.text}} for part in msg.parts],
                    "metadata": msg.metadata,
                }
            )

        self._make_sync_request(
            "load_messages", {"agent_id": self.agent_id, "messages": server_messages}
        )
