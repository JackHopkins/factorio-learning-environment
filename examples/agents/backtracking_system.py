import copy
from typing import Optional

from fle.commons.models.conversation import Conversation
from fle.commons.models.message import Message
from fle.env.namespace import FactorioNamespace

from fle.agents.models import CompletionResult, Response
from fle.agents.llm.parsing import Policy
from fle.agents.agent_abc import AgentABC
from fle.agents.backtracking_agent import BacktrackingAgent
from fle.agents.basic_agent import BasicAgent


class BacktrackingSystem(AgentABC):
    def __init__(
        self,
        model,
        system_prompt,
        task,
        agent_idx: Optional[int] = None,
        *args,
        **kwargs,
    ):
        self.backtracking_agent = BacktrackingAgent(
            model, system_prompt, task, *args, **kwargs
        )
        self.generator_agent = BasicAgent(
            model, system_prompt, task, agent_idx=agent_idx, *args, **kwargs
        )
        self.successful_conv = None
        self.last_successful_program_id = None
        self.task = task
        self.model = model
        self.system_prompt = self.generator_agent.system_prompt

    async def step(
        self,
        conversation: Conversation,
        response: Optional[Response],
        namespace: FactorioNamespace,
    ) -> Policy:
        if self.successful_conv is None:
            self.successful_conv = copy.deepcopy(conversation)
        if response and response.error and not self.backtracking_agent.memory_full:
            step_output = await self.backtracking_agent.step(
                self.successful_conv, response, namespace
            )
            return step_output[0], {
                "revision_of": response.program_id,
                "last_successful_program_id": self.last_successful_program_id,
            }
        else:
            # reset the step memory if the response was not an error
            self.backtracking_agent.clear_memory()
            if response and not response.error:
                latest_program_message = Message(
                    role="assistant", content=response.code, metadata={}
                )
                # Add the env message to the conversation
                env_message = Message(
                    role="user", content=response.response, metadata={}
                )
                self.successful_conv.messages.append(latest_program_message)
                self.successful_conv.messages.append(env_message)
                self.last_successful_program_id = response.program_id
            step_output = await self.generator_agent.step(
                self.successful_conv, response, namespace
            )
            return step_output[0], {
                "revision_of": None,
                "last_successful_program_id": self.last_successful_program_id,
            }

    def check_step_completion(self, response: Response) -> tuple[bool, bool]:
        """
        Check if the agent should complete its turn and if the state should be updated
        returns:
            - update_state: bool, True if the state should be updated
            - completed: bool, True if the agent should complete its turn
        """
        if response.error:
            print("Error occurred in program evaluation. Attemptingto error-correct.")
            if self.backtracking_agent.memory_full:
                # If the backtracking agent is full, we need to complete the turn but not update the state
                update_state, completed = False, True
            else:
                update_state, completed = False, False
        else:
            # If the response is not an error, we need to update the state and complete the turn
            update_state, completed = True, True
        return update_state, completed

    async def end(self, conversation: Conversation, completion: CompletionResult):
        pass
