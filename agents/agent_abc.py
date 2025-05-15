from abc import abstractmethod
from typing import List, Optional
import uuid
import os

from agents import Response, Python, CompletionResult, Policy
from env.src.models.conversation import Conversation
from env.src.namespace import FactorioNamespace
from env.src.protocols.a2a.handler import A2AProtocolHandler, AgentCard


class AgentABC:
    model: str
    system_prompt: str
    conversation: Conversation
    a2a_handler: Optional[A2AProtocolHandler] = None
    def __init__(self, model, system_prompt, *args, **kwargs):
       self.model = model
       self.system_prompt = system_prompt
       
    def _create_agent_card(self) -> AgentCard:
        """Create an A2A agent card describing this agent's capabilities"""
        return AgentCard(
            name=f"FactorioAgent_{self.model}",
            capabilities={
                "tools": self._get_available_tools(),
                "actions": self._get_available_actions(),
                "protocol_version": "1.0"
            },
            connection_info={
                "type": "factorio",
                "version": "1.0"
            }
        )

    def _get_available_tools(self) -> List[str]:
        """Get list of available tools for this agent"""
        # This should be implemented by subclasses
        return []

    def _get_available_actions(self) -> List[str]:
        """Get list of available actions for this agent"""
        # This should be implemented by subclasses
        return []
    
    def set_conversation(self, conversation: Conversation) -> None:
        """
        Overrides the current conversation state for this agent. This is useful for context modification strategies,
        such as summarisation or injection (i.e RAG).
        @param conversation: The new conversation state.
        @return:
        """
        self.conversation = conversation

    @abstractmethod
    async def step(self, conversation: Conversation, response: Response, namespace: FactorioNamespace) -> Policy:
        """
        A single step in a trajectory. This method should return the next policy to be executed, based on the last response.
        @param conversation: The current state of the conversation.
        @param response: The most recent response from the environment.
        @param namespace: The current namespace of the conversation, containing declared variables and functions.
        @return:
        """
        pass

    @abstractmethod
    async def end(self, conversation: Conversation, completion: CompletionResult):
        """
        Cleanup for when a trajectory ends
        """
        pass
    
    def check_completion(self, response: Response) -> tuple[bool, bool]:
        """
        Check if the agent should complete its turn and if the state should be updated
        returns:
            - update_state: bool, True if the state should be updated
            - completed: bool, True if the agent should complete its turn
        """
        # by default, we assume that the agent should complete its turn and update the state
        update_state, completed = True, True
        return update_state, completed

