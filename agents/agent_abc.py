from abc import abstractmethod

from agents import Response, Python, CompletionResult, Policy
from models.conversation import Conversation
from namespace import FactorioNamespace


class AgentABC:
    model: str
    system_prompt: str
    conversation: Conversation

    def __init__(self, model, system_prompt, *args, **kwargs):
       self.model = model
       self.system_prompt = system_prompt

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


