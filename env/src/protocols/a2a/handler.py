from typing import Dict, Any, Optional, List
import json
import time
import requests
import uuid
from pydantic import BaseModel


class AgentCard(BaseModel):
    """A2A Agent Card implementation"""
    name: str
    capabilities: Dict[str, Any]
    connection_info: Dict[str, Any]
    version: str = "1.0"


class A2AMessage(BaseModel):
    """Enhanced message format supporting A2A protocol"""
    sender: str
    recipient: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = {}
    message_type: str = "text"
    timestamp: float = time.time()
    is_new: bool = True


class AgentA2AConfig(BaseModel):
    agent_name: str
    capabilities: List[str]
    # Add other fields here if A2AProtocolHandler constructor needs them
    # based on its actual definition.
    # For now, matching agent_name and capabilities which are explicit in A2AProtocolHandler constructor.


class A2AProtocolHandler:
    def __init__(
        self,
        agent_id: str,
        server_url: str,
        agent_name: str = "FactorioAgent",
        capabilities: Optional[List[str]] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        self.agent_id = agent_id
        self.server_url = server_url
        self.agent_name = agent_name
        self.capabilities = capabilities or []
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._is_registered = False
        self._session = requests.Session()

    def __enter__(self):
        self.register()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_registered:
            self.unregister()
        self._session.close()
        self._session = None

    def _make_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        print(request)
        
        response = self._session.post(self.server_url, json=request)
        result = response.json()
        if "error" in result and result["error"] is not None:
            raise Exception(f"A2A protocol error: {result['error']}")
        return result.get("result", {})

    def register(self) -> None:
        """Register this agent with the A2A server"""
        self._make_request("register", {
            "agent_id": self.agent_id,
            "agent_card": {
                "name": self.agent_name,
                "capabilities": self.capabilities,
                "connection_info": {}
            }
        })
        self._is_registered = True

    def unregister(self) -> None:
        """Unregister this agent from the A2A server"""
        self._make_request("unregister", {
            "agent_id": self.agent_id
        })
        self._is_registered = False

    def discover_agents(self) -> List[Dict[str, Any]]:
        """Discover other agents registered with the A2A server"""
        result = self._make_request("discover", {})
        return result.get("agents", [])

    def negotiate_capabilities(self, agent_id: str, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Negotiate capabilities with another agent"""
        result = self._make_request("negotiate", {
            "agent_id": agent_id,
            "capabilities": capabilities
        })
        return result

    def send_message(self, message: A2AMessage) -> None:
        """Send a message to another agent through the A2A server"""
        self._make_request("send_message", {
            "sender_id": self.agent_id,
            "recipient_id": message.recipient,
            "message": message.dict()
        })

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get messages sent to this agent"""
        result = self._make_request("get_messages", {
            "agent_id": self.agent_id
        })
        return result.get("messages", [])

    def load_messages(self, messages: List[Dict[str, Any]]) -> None:
        """
        Load messages into the agent's message queue on the server.
        :param messages: List of message dictionaries to load
        """
        if not self._is_registered:
            raise Exception("Agent must be registered before loading messages")
            
        self._make_request("load_messages", {
            "agent_id": self.agent_id,
            "messages": messages
        }) 