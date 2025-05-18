import logging
from typing import Optional, List, Dict

from env.src.namespace import FactorioNamespace
from env.src.protocols.a2a.handler import A2AProtocolHandler

class A2AFactorioNamespace(FactorioNamespace):
    """A FactorioNamespace with A2A (Agent-to-Agent) communication support."""
    
    def __init__(self, instance, agent_index):
        self.a2a_handler: Optional[A2AProtocolHandler] = None
        self.called_setup = False
        super().__init__(instance, agent_index)
        logging.info(f"Namespace {self.agent_id}: Initializing A2A namespace")

    async def async_setup_default_a2a_handler(self, server_url: str):
        """Creates and registers a default A2AProtocolHandler for this namespace."""
        if self.a2a_handler and hasattr(self.a2a_handler, '_is_registered') and self.a2a_handler._is_registered:
            logging.warning(f"Namespace {self.agent_id}: A2A handler already exists and is registered. Unregistering existing handler first.")
            try:
                await self.a2a_handler.__aexit__(None, None, None)
            except Exception as e:
                logging.error(f"Namespace {self.agent_id}: Error unregistering existing A2A handler: {e}", exc_info=True)
        
        agent_id_str = self.agent_id
        agent_name = f"FactorioAgent_{agent_id_str}"
        default_capabilities = {
            "tools": ["send_message", "render_message"], # Example default tools
            "actions": [],
            "protocol_version": "1.0"
        }

        self.a2a_handler = A2AProtocolHandler(
            agent_id=agent_id_str, # agent_id must be unique for the server
            server_url=server_url,
            agent_name=agent_name,
            capabilities=default_capabilities
        )
        try:
            logging.info(f"Namespace {agent_id_str}: Registering A2A handler with server {server_url}...")
            await self.a2a_handler.__aenter__()
            logging.info(f"Namespace {agent_id_str}: A2A handler registered successfully.")
            self.called_setup = True
            assert self.a2a_handler is not None
            logging.info(f"Namespace {agent_id_str}: A2A handler is not None")
        except Exception as e:
            logging.error(f"Namespace {agent_id_str}: Failed to register A2A handler: {e}", exc_info=True)
            self.a2a_handler = None # Clear handler if registration failed
            raise # Re-raise the exception so instance.py can see it

    def get_messages(self) -> List[Dict]:
        """
        Get all messages sent to this agent using the A2A protocol handler.
        :return: List of message dictionaries containing sender, message, timestamp, and recipient
        """
        try:
            # Get the A2A handler from the game state
            if not self.a2a_handler:
                if not self.called_setup:
                    raise Exception("A2A namespace not setup")
                else:
                    raise Exception("A2A handler not found in namespace")

            # Get messages using the A2A handler
            messages = self.a2a_handler.get_messages()
            
            # Convert A2A message format to our expected format
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    'sender': int(msg['sender']),
                    'message': msg['content'],
                    'timestamp': int(msg['timestamp']),
                    'recipient': int(msg['recipient']) if msg['recipient'] else None
                })
            
            print('got messages', formatted_messages)
            return formatted_messages
            
        except Exception as e:
            raise Exception(f"Error getting messages: {str(e)}")

    def load_messages(self, messages: List[Dict]) -> None:
        """
        Load messages into the A2A protocol handler's state.
        :param messages: List of message dictionaries containing sender, message, timestamp, and recipient
        """
        try:
            if not self.a2a_handler:
                raise Exception("A2A handler not found in namespace")

            # Convert our message format to A2A format
            a2a_messages = []
            for msg in messages:
                if not all(k in msg for k in ['sender', 'message', 'timestamp', 'recipient']):
                    raise ValueError("Message missing required fields: sender, message, timestamp, recipient")
                
                a2a_messages.append({
                    'sender': str(msg['sender']),
                    'content': msg['message'],
                    'timestamp': str(msg['timestamp']),
                    'recipient': str(msg['recipient']) if msg['recipient'] is not None else None
                })

            # Load messages into the A2A handler
            self.a2a_handler.load_messages(a2a_messages)
            
        except Exception as e:
            raise Exception(f"Error loading messages: {str(e)}") 