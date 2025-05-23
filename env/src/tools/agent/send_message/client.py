from typing import Any, Dict, Optional
import time
import asyncio
import threading
from pydantic import BaseModel
from env.src.tools.tool import Tool
from env.src.tools.admin.render_message.client import RenderMessage
from env.src.protocols.a2a.handler import A2AMessage, A2AProtocolHandler
import logging
import json
import requests


class SendMessage(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "send_message"
        self.namespace = game_state
        self.render_message = RenderMessage(connection, self.namespace)
        
        self.load()

    def __call__(self, 
                 message: str, 
                 recipient: Optional[str] = None,
                 message_type: str = "text",
                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send a message to other agents using the A2A protocol. (Synchronous wrapper)
        
        :param message: The message to send
        :param recipient: Optional recipient agent ID. If None, message is broadcast.
        :param message_type: Type of message (text, data, command, etc.)
        :param metadata: Additional metadata for the message
        :return: True if message was sent successfully, False otherwise (e.g. on timeout)
        """
        logging.debug(f"SendMessage: __call__ entered. Recipient: {recipient}, Type: {message_type}")

        if not self.game_state.instance.is_multiagent:
            logging.info("SendMessage: Skipping message in single agent mode")
            return True
        
        # Determine sender_id
        sender_id = None
        if hasattr(self.namespace, 'agent_id') and self.namespace.agent_id is not None:
            sender_id = str(self.namespace.agent_id)
        else:
            if hasattr(self.namespace, 'a2a_handler') and self.namespace.a2a_handler:
                if hasattr(self.namespace.a2a_handler, 'agent_id') and self.namespace.a2a_handler.agent_id is not None:
                    sender_id = str(self.namespace.a2a_handler.agent_id)
            
        if sender_id is None:
            logging.error("SendMessage: Failed to determine player/agent ID for sender.")
            return False
        
        # Get server URL from the namespace's a2a_handler
        server_url = None
        if hasattr(self.namespace, 'a2a_handler') and self.namespace.a2a_handler:
            server_url = getattr(self.namespace.a2a_handler, 'server_url', None)
        
        if not server_url:
            server_url = "http://localhost:8000/a2a"  # Default fallback with correct endpoint
            logging.warning(f"SendMessage: Using default server URL: {server_url}")
        
        # Create message payload
        a2a_message = {
            "sender": sender_id,
            "recipient": recipient,
            "content": message,
            "message_type": message_type,
            "metadata": metadata or {},
            "timestamp": time.time(),
            "is_new": True
        }
        
        # Create JSON-RPC request
        request_id = f"{time.time()}-{sender_id}"
        request = {
            "jsonrpc": "2.0",
            "method": "send_message",
            "params": {
                "sender_id": sender_id,
                "recipient_id": recipient,
                "message": a2a_message
            },
            "id": request_id
        }
        
        # Send request using synchronous requests library
        try:
            logging.debug(f"SendMessage: Sending message directly. Sender: {sender_id}, Recipient: {recipient}, Server: {server_url}")
            print(request)
            response = requests.post(server_url, json=request, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if "error" in result and result["error"]:
                    logging.error(f"SendMessage: Server returned error: {result['error']}")
                    return False
                logging.debug(f"SendMessage: Message successfully sent. Response: {result.get('result', {})}")
                self.render_message(message)
                return True
            else:
                logging.error(f"SendMessage: Server returned status code {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logging.warning(f"SendMessage: Timeout (10s) waiting for A2A message to be sent. Recipient: {recipient}, Type: {message_type}")
            return False
        except Exception as e:
            logging.error(f"SendMessage: Exception while sending A2A message. Recipient: {recipient}, Error: {str(e)}", exc_info=True)
            return False 