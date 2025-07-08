from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
from datetime import datetime
import requests
import multiprocessing
import time
import socket
import logging
from contextlib import contextmanager
import uuid

app = FastAPI()


# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


class ServerManager:
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.process = None
        self._lock = multiprocessing.Lock()

    def is_server_running(self) -> bool:
        """Check if the server is running by attempting to connect to the health endpoint"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=1)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def is_port_in_use(self) -> bool:
        """Check if the port is in use by attempting to bind to it"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.host, self.port))
                return False
            except socket.error:
                return True

    @staticmethod
    def run_server(host: str, port: int):
        """Static method to run the server"""
        uvicorn.run(app, host=host, port=port)

    def start_server(self):
        """Start the server in a separate process if it's not already running"""
        with self._lock:
            if self.is_server_running():
                logging.info(f"A2A server already running at {self.server_url}")
                return

            if self.is_port_in_use():
                logging.warning(
                    f"Port {self.port} is in use but server health check failed. Attempting to start server anyway."
                )

            self.process = multiprocessing.Process(
                target=self.run_server, args=(self.host, self.port)
            )
            self.process.daemon = (
                True  # Process will be terminated when main process exits
            )
            self.process.start()

            # Wait for server to start
            max_retries = 5
            retry_delay = 1
            for _ in range(max_retries):
                if self.is_server_running():
                    logging.info(f"A2A server started at {self.server_url}")
                    return
                time.sleep(retry_delay)

            # If we get here, server failed to start
            if self.process.is_alive():
                self.process.terminate()
            raise RuntimeError(f"Failed to start A2A server at {self.server_url}")

    def stop_server(self):
        """Stop the server if it's running"""
        with self._lock:
            if self.process and self.process.is_alive():
                self.process.terminate()
                self.process.join()
                logging.info(f"A2A server stopped at {self.server_url}")

    @contextmanager
    def ensure_server_running(self):
        """Context manager to ensure server is running during the context"""
        try:
            self.start_server()
            yield self.server_url
        finally:
            # Don't stop the server when exiting the context
            # This allows the server to keep running for other clients
            pass


class AgentRegistry:
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, List[Dict[str, Any]]] = {}

    def register_agent(self, agent_id: str, agent_card: Dict[str, Any]) -> None:
        self.agents[agent_id] = {
            "card": agent_card,
            "last_seen": datetime.utcnow().isoformat(),
            "status": "available",
        }
        if agent_id not in self.messages:
            self.messages[agent_id] = []

    def unregister_agent(self, agent_id: str) -> None:
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [
            {"id": agent_id, **agent_data}
            for agent_id, agent_data in self.agents.items()
        ]

    def store_message(
        self, sender_id: str, recipient_id: str, message: Dict[str, Any]
    ) -> None:
        if recipient_id not in self.messages:
            self.messages[recipient_id] = []
        self.messages[recipient_id].append(
            {
                "sender": sender_id,
                "messageId": message.get("messageId", str(uuid.uuid4())),
                "role": message.get("role", "user"),
                "content": message.get("parts", [{"root": {"text": ""}}])[0]["root"][
                    "text"
                ],
                "metadata": message.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_messages(self, agent_id: str) -> List[Dict[str, Any]]:
        messages = self.messages.get(agent_id, [])
        return messages

    def load_messages(self, agent_id: str, messages: List[Dict[str, Any]]) -> None:
        """
        Load messages into an agent's message queue.
        :param agent_id: The ID of the agent to load messages for
        :param messages: List of message dictionaries in A2A Message format
        """
        self.messages[agent_id] = []

        # Validate and store messages
        for msg in messages:
            if not all(k in msg for k in ["messageId", "role", "parts", "metadata"]):
                raise ValueError(
                    "Message missing required fields: messageId, role, parts, metadata"
                )

            # Extract text content from the first part
            content = msg["parts"][0]["root"]["text"] if msg["parts"] else ""

            self.messages[agent_id].append(
                {
                    "sender": msg["metadata"].get("sender", ""),
                    "recipient": msg["metadata"].get("recipient", ""),
                    "messageId": msg["messageId"],
                    "role": msg["role"],
                    "content": content,
                    "metadata": msg["metadata"],
                    "timestamp": msg["metadata"].get(
                        "timestamp", datetime.utcnow().isoformat()
                    ),
                }
            )


registry = AgentRegistry()


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@app.post("/a2a")
async def handle_jsonrpc(request: JSONRPCRequest) -> JSONRPCResponse:
    try:
        if request.method == "register":
            agent_id = request.params.get("agent_id")
            agent_card = request.params.get("agent_card")
            if not agent_id or not agent_card:
                raise HTTPException(
                    status_code=400, detail="Missing agent_id or agent_card"
                )
            registry.register_agent(agent_id, agent_card)
            return JSONRPCResponse(result={"status": "registered"}, id=request.id)

        elif request.method == "unregister":
            agent_id = request.params.get("agent_id")
            if not agent_id:
                raise HTTPException(status_code=400, detail="Missing agent_id")
            registry.unregister_agent(agent_id)
            return JSONRPCResponse(result={"status": "unregistered"}, id=request.id)

        elif request.method == "discover":
            return JSONRPCResponse(
                result={"agents": registry.list_agents()}, id=request.id
            )

        elif request.method == "negotiate":
            agent_id = request.params.get("agent_id")
            capabilities = request.params.get("capabilities", {})
            agent = registry.get_agent(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            # Simple capability negotiation - just return intersection of capabilities
            agent_capabilities = agent["card"].get("capabilities", {})
            supported = {
                k: v for k, v in agent_capabilities.items() if k in capabilities
            }
            return JSONRPCResponse(
                result={"supported_capabilities": supported, "status": "negotiated"},
                id=request.id,
            )

        elif request.method == "send_message":
            sender_id = request.params.get("sender_id")
            recipient_id = request.params.get("recipient_id")
            message_content = request.params.get("message", {})

            if not sender_id:
                raise HTTPException(status_code=400, detail="Missing sender_id")

            status_message = ""
            if recipient_id is None:
                # Handle broadcast: send to all registered agents except the sender
                agents_to_notify = [
                    agent_id
                    for agent_id in registry.agents.keys()
                    if agent_id != sender_id
                ]
                if not agents_to_notify:
                    status_message = "sent_broadcast_no_other_agents"
                else:
                    for target_agent_id in agents_to_notify:
                        # Ensure the recipient exists before trying to store
                        if registry.get_agent(target_agent_id):
                            registry.store_message(
                                sender_id, target_agent_id, message_content
                            )
                    status_message = f"sent_broadcast_to_{len(agents_to_notify)}_agents"
            else:
                # Handle targeted message: recipient_id must be a non-empty string and exist
                recipient_id = str(recipient_id)
                if not recipient_id.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid recipient_id (must be a non-empty string)",
                    )

                if not registry.get_agent(recipient_id):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Recipient agent_id '{recipient_id}' not found.",
                    )

                registry.store_message(sender_id, recipient_id, message_content)
                status_message = "sent_unicast"

            return JSONRPCResponse(result={"status": status_message}, id=request.id)

        elif request.method == "get_messages":
            agent_id = request.params.get("agent_id")
            if not agent_id:
                raise HTTPException(status_code=400, detail="Missing agent_id")

            messages = registry.get_messages(agent_id)
            return JSONRPCResponse(result={"messages": messages}, id=request.id)

        elif request.method == "load_messages":
            agent_id = request.params.get("agent_id")
            messages = request.params.get("messages", [])

            if not agent_id:
                raise HTTPException(status_code=400, detail="Missing agent_id")
            if not isinstance(messages, list):
                raise HTTPException(status_code=400, detail="Messages must be a list")

            try:
                registry.load_messages(agent_id, messages)
                return JSONRPCResponse(
                    result={"status": "messages_loaded"}, id=request.id
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown method: {request.method}"
            )

    except Exception as e:
        return JSONRPCResponse(error={"code": -32000, "message": str(e)}, id=request.id)


def start_server(host: str = "localhost", port: int = 8000):
    """Legacy function to start server directly"""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # Example usage of ServerManager
    manager = ServerManager()
    with manager.ensure_server_running() as server_url:
        print(f"Server is running at {server_url}")
        # Server will keep running until the script exits
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
