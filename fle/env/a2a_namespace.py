import logging
from typing import Dict, List, Optional

from a2a.types import AgentCard, Message, Part, TextPart
from fle.agents.agent_abc import create_default_agent_card

from fle.env.namespace import FactorioNamespace
from fle.env.protocols.a2a.handler import A2AProtocolHandler


class A2AFactorioNamespace(FactorioNamespace):
    """A FactorioNamespace with A2A (Agent-to-Agent) communication support."""

    def __init__(self, instance, agent_index):
        self.a2a_handler: Optional[A2AProtocolHandler] = None
        self.called_setup = False
        super().__init__(instance, agent_index)
        logging.info(f"Namespace {self.agent_id}: Initializing A2A namespace")

    async def async_setup_default_a2a_handler(
        self, server_url: str, agent_card: Optional[AgentCard] = None
    ):
        """Creates and registers a default A2AProtocolHandler for this namespace.

        :param server_url: URL of the A2A server
        :param agent_card: Optional AgentCard with agent capabilities and info
        """
        if (
            self.a2a_handler
            and hasattr(self.a2a_handler, "_is_registered")
            and self.a2a_handler._is_registered
        ):
            logging.warning(
                f"Namespace {self.agent_id}: A2A handler already exists and is registered. Unregistering existing handler first."
            )
            try:
                await self.a2a_handler.__aexit__(None, None, None)
            except Exception as e:
                logging.error(
                    f"Namespace {self.agent_id}: Error unregistering existing A2A handler: {e}",
                    exc_info=True,
                )

        agent_id_str = self.agent_id
        # Create default agent card if none provided
        if agent_card is None:
            agent_card = create_default_agent_card(agent_id_str)

        self.a2a_handler = A2AProtocolHandler(
            agent_id=agent_id_str, server_url=server_url, agent_card=agent_card
        )
        try:
            logging.info(
                f"Namespace {agent_id_str}: Registering A2A handler with server {server_url}..."
            )
            await self.a2a_handler.__aenter__()
            logging.info(
                f"Namespace {agent_id_str}: A2A handler registered successfully."
            )
            self.called_setup = True
            # do this to reset the messages for the agent.
            self.load_messages([])

        except Exception as e:
            logging.error(
                f"Namespace {agent_id_str}: Failed to register A2A handler: {e}",
                exc_info=True,
            )
            self.a2a_handler = None  # Clear handler if registration failed
            raise  # Re-raise the exception so instance.py can see it

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

            # Get messages using the A2A handler (now returns List[Message])
            messages = self.a2a_handler.get_messages()

            # Convert Message objects to our expected dictionary format
            formatted_messages = []
            for msg in messages:
                # Extract text content from the first part
                content = msg.parts[0].root.text if msg.parts else ""

                formatted_messages.append(
                    {
                        "messageId": msg.messageId,
                        "sender": msg.metadata.get("sender", ""),
                        "message": content,
                        "timestamp": int(msg.metadata.get("timestamp", 0)),
                        "recipient": msg.metadata.get("recipient"),
                    }
                )

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

            # Convert dictionary messages to A2A Message objects
            a2a_messages = []
            for msg in messages:
                if not all(
                    k in msg
                    for k in [
                        "sender",
                        "message",
                        "timestamp",
                        "recipient",
                        "messageId",
                    ]
                ):
                    raise ValueError(
                        "Message missing required fields: sender, message, timestamp, recipient, messageId"
                    )

                # Create Message object with proper structure
                a2a_message = Message(
                    messageId=msg["messageId"],
                    role="user",
                    parts=[Part(root=TextPart(text=msg["message"]))],
                    metadata={
                        "sender": str(msg["sender"]),
                        "message_type": "text",
                        "timestamp": str(msg["timestamp"]),
                        "recipient": str(msg["recipient"])
                        if msg["recipient"] is not None
                        else None,
                    },
                )
                a2a_messages.append(a2a_message)

            # Load messages into the A2A handler
            self.a2a_handler.load_messages(a2a_messages)

        except Exception as e:
            raise Exception(f"Error loading messages: {str(e)}")
