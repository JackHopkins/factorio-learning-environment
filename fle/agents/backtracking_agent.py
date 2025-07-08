import copy
from collections import deque
from typing import Optional

import tenacity
from tenacity import retry_if_exception_type, wait_exponential

from fle.commons.models.conversation import Conversation
from fle.commons.models.generation_parameters import GenerationParameters
from fle.commons.models.message import Message
from fle.env.namespace import FactorioNamespace

from fle.agents.models import CompletionResult, Response
from fle.agents.llm.parsing import Policy
from fle.agents.agent_abc import AgentABC
from fle.agents.formatters import RecursiveReportFormatter
from fle.agents.llm.api_factory import APIFactory
from fle.agents.llm.parsing import parse_response

GENERAL_INSTRUCTIONS_BACKTRACKING = """
# Factorio LLM Agent Instructions

## Overview
You are an AI agent designed to play Factorio, specializing in error correction and backtracking. Your goal is to analyze and fix Python code that interacts with the game environment. You will receive error messages and program outputs, and your task is to identify the root cause of the errors and provide corrected code.

## Environment Structure
- Operates like an interactive Python shell
- Agent messages = Python programs to execute
- User responses = STDOUT/STDERR from REPL
- Interacts through 27 core API methods (to be specified)

## Response Format
You are given a program or a history of programs that the agent wrote but that errored out the environment. You must analyse the error and return a fixed version of the program. Analyze the root cause of entities that aren't working, and prioritize automated solutions (like transport belts) above manual triage
CARRY OUT THE FOLLOWING 2 STAGES:
- PLANNING: Think through each step extensively in natural language
- POLICY: Write the fixed and improved Python code to execute the planned actions
### 1. PLANNING Stage
Think through each step extensively in natural language, addressing:
1. Error Analysis
Address each of the following questions:
   - What was the potential cause of the error?
   - Which line did the error happen at?
   - Was the program too long and a shorter program would be preferred? USE MAXIMUM 20 LINES OF CODE. If the original was too long, Identify the first short part and only return that part. Too long programs are not allowed and cause errors
   - What needs to be changed to fix the program and it not erroring out anymore
### 2. POLICY Stage
Write the fixed and improved Python code to execute the planned actions:
```python
# Code must be enclosed in Python tags
your_code_here
```

IMPORTANT: The last steps errored out and hence the game state was not altered from the last successful step. You must output full policy that will interact with the game state from the last successful step.

## Best Practices

### Modularity
- Create small, modular policies, MAXIMUM 20 LINES OF CODE
- Each policy should have a single clear purpose
- Keep policies easy to debug and modify
- Avoid breaking existing automated structures
- Encapsulate working logic into functions if needed

### Debugging & Verification
- Use print statements to monitor important state
- Implement assert statements for self-verification
- Use specific, parameterized assertion messages
- Example: `assert condition, f"Expected {expected}, got {actual}"`

### State Management
- Consider entities needed for each step
- Track entities across different inventories
- Monitor missing requirements
- Preserve working automated structures

### Code Structure
- Write code as direct Python interpreter commands
- Only encapsulate reusable utility code into functions 
- Use appropriate spacing and formatting

## Understanding Output

### Error Messages
```stderr
Error: 1: ("Initial Inventory: {...}")
10: ("Error occurred in following lines...")
```
- Numbers indicate line of execution
- Previous lines executed successfully
- Fix errors at indicated line

### Status Updates
```stdout
23: ('Resource collection completed...')
78: ('Entities on map: [...]')
```
- Shows execution progress
- Provides entity status
- Lists warnings and conditions

### Entity Status Checking
- Monitor entity `warnings` field
- Check entity `status` field
- Verify resource levels
- Track production states


## Utility Functions
- Create functions to encapsulate proven, reusable logic
- Place function definitions before their first use
- Document function purpose, parameters, and return values
- Test functions thoroughly before relying on them
- Example:
```python
def find_idle_furnaces(entities):
    \"\"\"Find all furnaces that are not currently working.
    
    Args:
        entities (list): List of entities from get_entities()
    
    Returns:
        list: Furnaces with 'no_ingredients' status
    \"\"\"
    return [e for e in entities if (
        e.name == 'stone-furnace' and 
        e.status == EntityStatus.NO_INGREDIENTS
    )]
```

## Data Structures
- Use Python's built-in data structures to organize entities
- Sets for unique entity collections:
```python
working_furnaces = {e for e in get_entities() 
                   if e.status == EntityStatus.WORKING}
```
- Dictionaries for entity mapping:
```python
furnace_by_position = {
    (e.position.x, e.position.y): e 
    for e in get_entities() 
    if isinstance(e, Furnace)
}
```
- Lists for ordered operations:
```python
sorted_furnaces = sorted(
    get_entities(),
    key=lambda e: (e.position.x, e.position.y)
)
```

## Important Notes
- Use transport belts to keep burners fed with coal
- Always inspect game state before making changes
- Consider long-term implications of actions
- Maintain working systems, and clear entities that aren't working or don't have a clear purpose
- Build incrementally and verify each step
- Do not encapsulate your code in a function _unless_ you are writing a utility for future use - just write it as if you were typing directly into the Python interpreter.
- Your inventory has space for ~2000 items. If it fills up, insert the items into a chest.
- Ensure that your factory is arranged in a grid, as this will make things easier.
"""

FINAL_INSTRUCTION = """## Frequent error modes to remember
- Forgeting to rotate inserters when they need to insert items into a machine. Use the rotate_inserter function to rotate inserters when needed. When inserters need to take items from a machine, they do not need to be rotated after placing next to a entity
- Errors like "Cannot connect to source inserter drop_position position x=18.5 y=81.5 as it is already occupied by following entities - ['wooden-chest at x=18.5 y=81.5'].",)" usually mean you need to rotate the inserter the other way around 
- Use drill.position when placing furnaces to catch outputs of a drill in place_entity_next_to. Furnaces are multiple tiles wide and using drill.drop_pos will break the placement. VERY IMPORTANT CONSIDERATION
- When fixing power setups that previously worked, often all you need to do is refuel the boiler. If a power setup works, then you dont need to change anything in the layout.
- Writing long and difficult to debug programs
- Incorrectly doing many-to-one connections (many source inserters to one target inserter). Analyse the examples and apply best practices. First connect one entity and then connect the other entities to that main connection 
- When you need to use water for a chemical plant or oil refinery, put down a new offshore pump! Do not use existing pumps as they likely already have pipes going out and the connection will likely error out.
- When placing inserters with place_entity_next_to, always use 0 spacing as the inserter needs to benext to the entity. Using spacing higher than 0 will put the insertes too far away from target entity and break the factory
"""


class BacktrackingAgent(AgentABC):
    def __init__(self, model, system_prompt, task, *args, **kwargs):
        backtrack_instructions = (
            GENERAL_INSTRUCTIONS_BACKTRACKING + system_prompt + FINAL_INSTRUCTION
        )
        self.task = task
        backtrack_instructions += f"\n\n### General Goal\n{task.goal_description}\n\n"
        self.instructions = backtrack_instructions
        super().__init__(model, backtrack_instructions, *args, **kwargs)
        self.api_factory = APIFactory(model)
        self.formatter = RecursiveReportFormatter(
            chunk_size=16,
            llm_call=self.api_factory.acall,
            cache_dir=".fle/summary_cache",
        )
        self.generation_params = GenerationParameters(n=1, max_tokens=2048, model=model)
        self.current_step_memory = deque([])
        self.max_nr_of_steps = 8  # original + fixing attempts
        self.current_step = 0

    def create_backtracking_conversation(
        self, conversation: Conversation, namespace: FactorioNamespace, response
    ) -> Conversation:
        system_message = Message(role="system", content=self.instructions)
        # We add the system message to the conversation
        new_conversation = Conversation(messages=[system_message])
        # Add the last 2 messages from the conversation to the new conversation
        new_conversation.messages.extend(conversation.messages[-2:])
        # add the "last successful step" tag to the last message
        new_conversation.messages[
            -1
        ].content = f"Last successful step:\n\n{new_conversation.messages[-1].content}\n\n This is the environment state before the error occurred. The environment has not been altered since the last successful step"
        latest_program = (
            f"Original attempt at carrying out the next step:\n\n```python{response.code}```"
            if len(self.current_step_memory) == 0
            else f"Error fixing attempt number {len(self.current_step_memory)}:\n\n```python{response.code}```"
        )
        # Add the latest program to the conversation
        latest_program_message = Message(
            role="assistant", content=latest_program, metadata={}
        )
        error_mesasage_str = f"Error message:\n\n{response.response}\n\n NB: This is the error message from the failed attempt. The environment has not been altered since the last successful step"
        # Add the error message to the conversation
        error_message = Message(role="user", content=error_mesasage_str, metadata={})
        # Add the error message to the step memory
        self.current_step_memory.append(
            {
                "assistant_message": latest_program_message,
                "environment_message": error_message,
            }
        )
        # If the step memory is too long, remove the oldest step but keep the first one
        if len(self.current_step_memory) > self.max_nr_of_steps:
            original_attempt = self.current_step_memory.popleft()
            # remove another step from the memory
            self.current_step_memory.popleft()
            # add the original attempt back to the memory
            self.current_step_memory.appendleft(original_attempt)
        # add the step memory to the conversation
        for step in self.current_step_memory:
            new_conversation.messages.append(step["assistant_message"])
            new_conversation.messages.append(step["environment_message"])
        return new_conversation

    async def step(
        self,
        conversation: Conversation,
        response: Optional[Response],
        namespace: FactorioNamespace,
    ) -> Policy:
        conversation = self.create_backtracking_conversation(
            conversation, namespace, response
        )
        temp_conv = Conversation(messages=copy.deepcopy(conversation.messages[3:]))
        temp_conv = await self.formatter.format_conversation(temp_conv, namespace)
        # merge the convs
        formatted_conversation = Conversation(
            messages=conversation.messages[:3] + temp_conv.messages
        )

        return await self._get_policy(formatted_conversation), None

    @tenacity.retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _get_policy(self, conversation: Conversation):
        response = await self.api_factory.acall(
            messages=self.formatter.to_llm_messages(conversation),
            n_samples=1,  # We only need one program per iteration
            temperature=self.generation_params.temperature,
            max_tokens=self.generation_params.max_tokens,
            model=self.generation_params.model,
        )

        policy = parse_response(response)
        if not policy:
            raise Exception("Not a valid Python policy")
        policy.input_conversation = conversation
        return policy

    def clear_memory(self):
        self.current_step = 0
        self.current_step_memory = deque([])

    @property
    def memory_full(self):
        return len(self.current_step_memory) >= self.max_nr_of_steps

    async def end(self, conversation: Conversation, completion: CompletionResult):
        pass
