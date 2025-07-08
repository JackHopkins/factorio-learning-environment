from typing import Any, Dict, Optional
import time
from fle.env.tools import Tool
from fle.env.tools.admin.render_message.client import RenderMessage
import logging
import uuid
from a2a.types import Message, Part, TextPart


class SendMessage(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)
        self.name = "send_message"
        self.namespace = game_state
        self.render_message = RenderMessage(connection, self.namespace)

        self.load()

    def __call__(
        self,
        message: str,
        recipient: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a message to other agents using the A2A protocol. (Synchronous wrapper)

        :param message: The message to send
        :param recipient: Optional recipient agent ID. If None, message is broadcast.
        :param message_type: Type of message (text, data, command, etc.)
        :param metadata: Additional metadata for the message
        :return: True if message was sent successfully, False otherwise (e.g. on timeout)
        """

        if not self.game_state.instance.is_multiagent:
            logging.info("SendMessage: Skipping message in single agent mode")
            return True

        # Check if we have a valid a2a_handler
        if not hasattr(self.namespace, "a2a_handler") or not self.namespace.a2a_handler:
            logging.error("SendMessage: No A2A handler available")
            return False

        try:
            # Create message payload using A2A Message schema
            a2a_message = Message(
                messageId=str(uuid.uuid4()),
                role="agent",
                parts=[Part(root=TextPart(text=message))],
                metadata={
                    "sender": self.namespace.agent_id,
                    "message_type": "text",
                    "timestamp": time.time(),
                    "recipient": recipient,
                },
            )

            # Use the synchronous send_message method
            self.namespace.a2a_handler.send_message(a2a_message)

            logging.debug("SendMessage: Message successfully sent via a2a_handler")
            self.render_message(message)
            return True

        except Exception as e:
            logging.error(
                f"SendMessage: Exception while sending A2A message. Recipient: {recipient}, Error: {str(e)}",
                exc_info=True,
            )
            return False
