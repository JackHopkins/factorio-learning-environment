from abc import ABC, abstractmethod
from env.src.models.game_state import GameState
from typing import List
from definitions import Step, Execution, AgentOutput, Agent

# Copied from agents/basic_agent.py
import tenacity
import json

from agents import Response, CompletionResult, Policy
from agents.agent_abc import AgentABC
from agents.utils.llm_factory import LLMFactory
from agents.utils.parse_response import parse_response
from models.conversation import Conversation
from models.generation_parameters import GenerationParameters
from tenacity import (
    wait_exponential,
    retry_if_exception_type,
    wait_random_exponential,
    stop_after_attempt,
)
from freeplay.recursive_report_formatter import RecursiveReportFormatter
import logging
from definitions import Message, ParsedGameState

from namespace import FactorioNamespace
from freeplay.conversation_formatter import ConversationFormatter

GENERAL_INSTRUCTIONS = """
# Factorio LLM Agent Instructions

## Overview
You are an AI agent designed to play Factorio, specializing in:
- Long-horizon planning
- Spatial reasoning 
- Systematic automation

## Environment Structure
- Operates like an interactive Python shell
- Agent messages = Python programs to execute
- User responses = STDOUT/STDERR from REPL
- Interacts through 27 core API methods (to be specified)

## Best Practices

### Modularity
- Create small, modular policies
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

### Error Handling
- Fix errors as they occur
- Don't repeat previous steps
- Continue from last successful execution
- Avoid unnecessary state changes
- Analyze the root cause of entities that aren't working, and prioritize automated solutions (like transport belts) above manual triage

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

## Game Progression
- Think about long term objectives, and break them down into smaller, manageable steps.
- Advance toward more complex automation
- Build on previous successes
- Maintain efficient resource usage

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
- DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off. Take into account what was the last action that was executed and continue from there. If there was a error previously, do not repeat your last lines - as this will alter the game state unnecessarily.
- Do not encapsulate your code in a function _unless_ you are writing a utility for future use - just write it as if you were typing directly into the Python interpreter.
- Your inventory has space for ~2000 items. If it fills up, insert the items into a chest.
- Ensure that your factory is arranged in a grid, as this will make things easier.
- Try to assign a specific and clear role to each entity, and ensure that it is working as expected. Check if similar entities are already present on the map. If exists, try to reuse them or fix the issues with them.
"""

FINAL_INSTRUCTION = """"
## Step Input
You are given updated state of existing entities on map and your inventory at each step.
You are supposed to take a look at these information carefully to plan your next step.

- You can place nothing but entities in your current inventory. If you don't have any entities in your inventory, you need to get them first by crafting, harvesting or smelting etc.
- Try to understand the role of each exsting entities on map. For example, one stone furnace might be used to smelt iron ore into iron plates, while another one might be used to smelt copper ore into copper plates, or to smelt iron plates into steel plates.
- In opposite, not-working entities have no use in the game. If you need to place some entities, you should first consider replacing existing ones. Example abundoned pipes or belts, not-working inserters, or empty chests.

## Response Format

### 1. PLANNING Stage
Think through each step extensively in natural language, addressing:
1. Error Analysis
   - Was there an error in the previous execution?
   - If yes, what was the problem?
2. Next Step Planning
   - What is the most useful next step of reasonable size?
   - Why is this step valuable?
   - Should I 
3. Action Planning
   - What specific actions are needed?
   - What resources are required?

### 2. POLICY Stage
Write Python code to execute the planned actions:
```python
# Code must be enclosed in Python tags
your_code_here
```

Your output should be in the following format:
[Planning]
your_planning_here

[Policy]
```python
your_code_here
```
"""


def my_before_sleep(retry_state):
    if retry_state.attempt_number < 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING
    logging.log(
        loglevel,
        "Retrying %s: attempt %s ended with: %s",
        retry_state.fn,
        retry_state.attempt_number,
        retry_state.outcome,
    )


class BasicAgent(Agent):
    def __init__(self, model, system_prompt):
        goal_description = "\n\n### Your Final Goal\n- Build the biggest possible factory\n- Maximise automation, efficiency and scale\n\n"
        instructions = GENERAL_INSTRUCTIONS + system_prompt + goal_description
        self.system_prompt = instructions

        self.llm_factory = LLMFactory(model)
        self.generation_params = GenerationParameters(n=1, max_tokens=2048, model=model)

    async def run(
        self,
        step: Step,
        game_state: ParsedGameState,
        execution_history: List[Execution],
    ) -> AgentOutput:
        messages = self._format_messages(step, game_state, execution_history)
        return await self._get_policy(messages)

    def _format_messages(
        self,
        step: Step,
        game_state: ParsedGameState,
        execution_history: List[Execution],
    ) -> List[Message]:
        updated_system_prompt = f"""
{self.system_prompt}

{FINAL_INSTRUCTION}

{step.instruction}
"""

        messages = (
            [
                Message(
                    role="system",
                    content=updated_system_prompt,
                )
            ]
            # + iteration_messages
            + [
                Message(
                    role="user",
                    content=f"""
## Existing Entities on Map
{game_state.entities}

## Your Inventory
{game_state.raw.inventory}

Remember that your python code must be always enclosed with ```python ... ``` decorator. It's very import for parsing your code. It you can't, you will be fired.

Your output
[Planning]""",
                ),
            ]
        )

        return messages

    @tenacity.retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before_sleep=my_before_sleep,
        stop=stop_after_attempt(3),
    )
    async def _get_policy(self, messages: List[Message]) -> AgentOutput:
        response = await self.llm_factory.acall(
            messages=[{"role": msg.role, "content": msg.content} for msg in messages],
            n_samples=1,  # We only need one program per iteration
            temperature=self.generation_params.temperature,
            max_tokens=self.generation_params.max_tokens,
            model=self.generation_params.model,
        )

        policy = parse_response(response)
        if not policy:
            raise Exception("Not a valid Python policy")

        return AgentOutput(
            input_messages=messages,
            raw_response=policy.meta.text_response,
            thinking=policy.thinking,
            code=policy.code,
        )
