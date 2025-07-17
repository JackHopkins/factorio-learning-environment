import copy
from typing import Any, Optional

from fle.env.gym_env.observation import Observation

from fle.commons.models.conversation import Conversation
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.program import Program
from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.eval.tasks import TaskABC

from fle.agents.models import CompletionResult
from fle.agents.llm.parsing import Policy
from fle.agents.agent_abc import AgentABC
from fle.agents.formatters import RecursiveReportFormatter
from fle.agents.llm.api_factory import APIFactory
from fle.agents.llm.parsing import parse_response

GYM_AGENT_INSTRUCTIONS = """
# Factorio Gym Agent Instructions

## Overview
You are an AI agent designed to play Factorio through a gym environment, specializing in:
- Long-horizon planning
- Spatial reasoning 
- Systematic automation

## Environment Structure
- Operates through gym observations and actions
- Agent actions = Python programs to execute
- Observations contain game state information
- Interacts through core API methods

## Response Format

### 1. PLANNING Stage
Think through each step extensively in natural language, addressing:
1. State Analysis
   - What is the current game state?
   - What resources and entities are available?
2. Next Step Planning
   - What is the most useful next step of reasonable size?
   - Why is this step valuable?
3. Action Planning
   - What specific actions are needed?
   - What resources are required?

### 2. POLICY Stage
Write Python code to execute the planned actions:
```python
# Code must be enclosed in Python tags
your_code_here
```

## Best Practices

### Modularity
- Create small, modular policies, MAXIMUM 30 lines of code
- Each policy should have a single clear purpose
- Keep policies easy to debug and modify
- Avoid breaking existing automated structures
- Encapsulate working logic into functions if needed

### State Management
- Consider entities needed for each step
- Track entities across different inventories
- Monitor missing requirements
- Preserve working automated structures

### Code Structure
- Write code as direct Python interpreter commands
- Only encapsulate reusable utility code into functions 
- Use appropriate spacing and formatting

## Understanding Observations

### Inventory
- List of items with quantities
- Monitor resource levels
- Track production states

### Entities
- List of entities on the map
- Includes type, position, direction, health
- Use for spatial reasoning

### Production Flows
- Input and output rates
- Monitor production efficiency
- Track resource consumption

### Game Info
- Current tick and time
- Game speed
- Use for timing decisions

## Important Notes
- Use transport belts to keep burners fed with coal
- Always inspect game state before making changes
- Consider long-term implications of actions
- Maintain working systems
- Build incrementally and verify each step
- DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off
- Do not encapsulate your code in a function _unless_ you are writing a utility for future use
- Your inventory has space for ~2000 items. If it fills up, insert the items into a chest
- Ensure that your factory is arranged in a grid
- Prefer manual fueling for boilers
{system_prompt}

ALWAYS WRITE VALID PYTHON AND REMEMBER MAXIMUM 30 LINES OF CODE PER POLICY. YOUR WEIGHTS WILL BE ERASED IF YOU DON'T USE PYTHON.

{goal_description}

{agent_instructions}"""


class GymAgent(AgentABC):
    def __init__(
        self,
        model: str,
        system_prompt: str,
        task: Any,
        agent_idx: Optional[int] = None,
        observation_formatter: Optional[BasicObservationFormatter] = None,
        *args,
        **kwargs,
    ):
        instructions = self._get_instructions(system_prompt, task, agent_idx)
        super().__init__(model, instructions, *args, **kwargs)
        self.task = task
        self.api_factory = APIFactory(model)
        self.observation_formatter = (
            observation_formatter or BasicObservationFormatter()
        )
        self.conversation = Conversation()
        self.formatter = RecursiveReportFormatter(
            chunk_size=16,
            llm_call=self.api_factory.acall,
            cache_dir=".fle/summary_cache",
        )
        self.generation_params = GenerationParameters(n=1, max_tokens=4096, model=model)

    def _get_instructions(
        self, system_prompt: str, task: TaskABC, agent_idx: Optional[int] = None
    ):
        agent_instructions = ""
        if agent_idx is not None and task.get_agent_instructions(agent_idx) is not None:
            player_idx = agent_idx + 1
            agent_instructions = f"### Specific Instructions for Agent {player_idx}\n{task.get_agent_instructions(agent_idx)}\n\n"
        instructions = GYM_AGENT_INSTRUCTIONS.format(
            system_prompt=system_prompt,
            goal_description=task.goal_description,
            agent_instructions=agent_instructions,
        )
        return instructions

    def reset(self, conversation: Conversation):
        self.conversation = copy.deepcopy(conversation)
        if self.conversation.messages[0].role != "system":
            self.conversation.set_system_message(self.system_prompt)

    async def update_conversation(
        self, observation: Observation, previous_program: Optional[Program] = None
    ):
        if previous_program:
            formatted_program = f"```python\n{previous_program.code}\n```"
            self.conversation.add_agent_message(formatted_program)

        formatted_obs = self.observation_formatter.format(observation).raw_str
        self.conversation.add_user_message(formatted_obs)
        self.conversation = await self.formatter.format_conversation(self.conversation)

    async def generate_policy(
        self,
        observation: Optional[Observation] = None,
        previous_program: Optional[Program] = None,
    ) -> Policy:
        """Generate a policy from the current observation.

        Returns:
            Policy if generation was successful, None otherwise
        """
        if observation:
            await self.update_conversation(observation, previous_program)
        try:
            model_response = await self.api_factory.acall(
                messages=self.formatter.to_llm_messages(self.conversation),
                n_samples=1,
                temperature=self.generation_params.temperature,
                max_tokens=self.generation_params.max_tokens,
                model=self.generation_params.model,
            )
            policy = parse_response(model_response)
            if not policy:
                raise Exception("Policy not valid Python. Skipping.")
            policy.input_conversation = self.conversation
            return policy

        except Exception as e:
            print(f"Policy generation failed: {str(e)}")
            return None

    async def step(self, conversation: Conversation) -> Policy:
        pass

    async def end(self, completion: CompletionResult):
        """Cleanup when the trajectory ends"""
        pass
