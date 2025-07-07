from abc import abstractmethod

from a2a.types import AgentCapabilities, AgentCard, AgentProvider, AgentSkill

from fle.commons.models.conversation import Conversation
from fle.env.namespace import FactorioNamespace

from fle.agents.models import CompletionResult, Response
from fle.agents.llm.parsing import Policy


class AgentABC:
    model: str
    system_prompt: str
    conversation: Conversation

    def __init__(self, model, system_prompt, *args, **kwargs):
        self.model = model
        self.system_prompt = system_prompt
        self.conversation = None

    def get_agent_card(self) -> AgentCard:
        """Get the agent card for this agent"""
        return create_default_agent_card(self.__class__.__name__)

    def set_conversation(self, conversation: Conversation) -> None:
        """
        Overrides the current conversation state for this agent. This is useful for context modification strategies,
        such as summarisation or injection (i.e RAG).
        @param conversation: The new conversation state.
        @return:
        """
        self.conversation = conversation

    @abstractmethod
    async def step(
        self,
        conversation: Conversation,
        response: Response,
        namespace: FactorioNamespace,
    ) -> Policy:
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

    def check_step_completion(self, response: Response) -> tuple[bool, bool]:
        """
        Check if the agent should complete its turn and if the state should be updated
        returns:
            - update_state: bool, True if the state should be updated
            - completed: bool, True if the agent should complete its turn
        """
        # by default, we assume that the agent should complete its turn and update the state
        update_state, completed = True, True
        return update_state, completed


def create_default_agent_card(name: str) -> AgentCard:
    """Create a default A2A agent card describing a Factorio agent's capabilities"""
    return AgentCard(
        name=name,
        version="1.0",
        description="An AI agent specialized in Factorio game automation and assistance",
        url="https://github.com/JackHopkins/factorio-learning-environment",
        capabilities=AgentCapabilities(
            pushNotifications=False, stateTransitionHistory=False, streaming=False
        ),
        defaultInputModes=["text/plain", "application/json"],
        defaultOutputModes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="factorio_automation",
                name="Factorio Automation",
                description="Automate and optimize Factorio gameplay",
                tags=["automation", "optimization", "gameplay"],
                examples=[
                    "Automate resource gathering",
                    "Optimize production lines",
                    "Design efficient layouts",
                ],
            ),
        ],
        provider=AgentProvider(
            organization="FLE team",
            url="https://github.com/JackHopkins/factorio-learning-environment",
        ),
    )
