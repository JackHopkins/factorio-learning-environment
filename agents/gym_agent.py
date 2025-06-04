from gym_env.observation_formatter import BasicObservationFormatter
import tenacity
from typing import Dict, Any, Optional, Tuple

from agents import Response, CompletionResult, Policy
from agents.agent_abc import AgentABC
from agents.utils.formatters.recursive_report_formatter import RecursiveReportFormatter
from agents.utils.llm_factory import LLMFactory
from agents.utils.parse_response import parse_response
from env.src.models.conversation import Conversation
from env.src.models.message import Message as ConvMessage
from env.src.models.generation_parameters import GenerationParameters
from env.src.models.program import Program
from env.src.gym_env.observation import AgentMessage, Observation
from env.src.namespace import FactorioNamespace
from tenacity import wait_exponential, retry_if_exception_type

GENERAL_INSTRUCTIONS = \
"""
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
"""

FINAL_INSTRUCTION = "\n\nALWAYS WRITE VALID PYTHON AND REMEMBER MAXIMUM 30 LINES OF CODE PER POLICY. YOUR WEIGHTS WILL BE ERASED IF YOU DON'T USE PYTHON."

class GymAgent(AgentABC):
    def __init__(self, model: str, system_prompt: str, task: Any, agent_idx: Optional[int] = None, observation_formatter: Optional[BasicObservationFormatter] = None, *args, **kwargs):
        instructions = self.get_instructions(system_prompt, task, agent_idx)
        super().__init__(model, instructions, *args, **kwargs)
        self.task = task
        self.llm_factory = LLMFactory(model)
        self.observation_formatter = observation_formatter or BasicObservationFormatter()
        self.formatter = RecursiveReportFormatter(
            chunk_size=16,
            llm_call=self.llm_factory.acall,
            cache_dir='summary_cache'
        )
        self.generation_params = GenerationParameters(
            n=1,
            max_tokens=4096,
            model=model
        )
        self.last_response = None

    async def step(self, conversation: Conversation) -> Policy:
        pass

    async def end(self, conversation: Conversation, completion: CompletionResult):
        """Cleanup when the trajectory ends"""
        pass


    def reset(self, observation: Observation):
        formatted_obs = self.observation_formatter.format(observation).raw_str
        self.conversation = Conversation(
            messages=[
                ConvMessage(role="system", content=self.system_prompt),
                ConvMessage(role="user", content=formatted_obs),
            ]
        )

    def get_instructions(self, system_prompt: str, task: Any, agent_idx: Optional[int] = None):
        instructions = GENERAL_INSTRUCTIONS + system_prompt + FINAL_INSTRUCTION
        instructions += f"\n\n### Goal\n{task.goal_description}\n\n"
        if agent_idx is not None and task.get_agent_instructions(agent_idx) is not None:
            player_idx = agent_idx + 1
            instructions += f"### Specific Instructions for Agent {player_idx}\n{task.get_agent_instructions(agent_idx)}\n\n"
        return instructions

    async def update_conversation(self, program: Program, observation: Observation):
        formatted_program = f"```python\n{program.code}\n```"
        formatted_obs = self.observation_formatter.format(observation).raw_str

        self.conversation.add_result(formatted_program, formatted_obs)
        self.conversation = await self.formatter.format_conversation(self.conversation)
        self.last_response = observation.raw_text


#    @tenacity.retry(
#        retry=retry_if_exception_type(Exception),
#        wait=wait_exponential(multiplier=1, min=4, max=10)
#    )
    async def generate_program(self, agent_idx: int, version: int, version_description: str, process_id: int) -> Program:
        """Generate a program from the current observation.
        
        Args:
            observation_dict: Dictionary containing the current observation state
            agent_idx: Index of the agent in the multi-agent setup
            version: Version number for the program
            version_description: Description of the version
            process_id: ID of the current process
            
        Returns:
            Program if generation was successful, None otherwise
        """
        try:
            model_response = await self.llm_factory.acall(
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

            # get depth
            messages = policy.input_conversation.model_dump()['messages']
            depth = len(messages) - 2

            # Create program from policy
            program = Program(
                code=policy.code,
                conversation=policy.input_conversation if policy.input_conversation else self.conversation,
                response=self.last_response,
                token_usage=policy.meta.total_tokens,
                completion_token_usage=policy.meta.output_tokens,
                prompt_token_usage=policy.meta.input_tokens,
                version=version,
                instance=agent_idx,
                model=self.model,
                version_description=version_description,
                meta={
                    "model": self.model,
                    "process_id": process_id
                },
                depth=depth
            )

            return program

        except Exception as e:
            print(f"Program generation failed: {str(e)}")
            return

