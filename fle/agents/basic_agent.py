from typing import Optional

import tenacity
from fle.env.namespace import FactorioNamespace
from tenacity import retry_if_exception_type, wait_exponential

from fle.commons.models.conversation import Conversation
from fle.commons.models.generation_parameters import GenerationParameters

from fle.agents.models import CompletionResult, Response
from fle.agents.llm.parsing import Policy
from fle.agents.agent_abc import AgentABC
from fle.agents.formatters.recursive_report_formatter import RecursiveReportFormatter
from fle.agents.llm.api_factory import APIFactory
from fle.agents.llm.metrics import timing_tracker, track_timing_async
from fle.agents.llm.parsing import parse_response

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

## Best Practices

### Modularity
- Create small, modular policies, MAXIMUM 30 lines of code
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
- Its a lot easier to manually add coil to boilers rather than make a automated system for it. Prefer manual fueling
"""

FINAL_INSTRUCTION = "\n\nALWAYS WRITE VALID PYTHON AND REMEMBER MAXIMUM 30 LINES OF CODE PER POLICY. YOUR WEIGHTS WILL BE ERASED IF YOU DON'T USE PYTHON."  # Annoying how effective this is


class BasicAgent(AgentABC):
    def __init__(
        self,
        model,
        system_prompt,
        task,
        agent_idx: Optional[int] = None,
        *args,
        **kwargs,
    ):
        instructions = GENERAL_INSTRUCTIONS + system_prompt + FINAL_INSTRUCTION
        self.task = task
        instructions += f"\n\n### Goal\n{task.goal_description}\n\n"
        if agent_idx is not None and task.get_agent_instructions(agent_idx) is not None:
            player_idx = agent_idx + 1
            instructions += f"### Specific Instructions for Agent {player_idx}\n{task.get_agent_instructions(agent_idx)}\n\n"
        super().__init__(model, instructions, *args, **kwargs)
        self.api_factory = APIFactory(model)
        self.formatter = RecursiveReportFormatter(
            chunk_size=16,
            llm_call=self.api_factory.acall,
            cache_dir=".fle/summary_cache",
        )
        self.generation_params = GenerationParameters(n=1, max_tokens=4096, model=model)

    @track_timing_async("agent_step")
    async def step(
        self,
        conversation: Conversation,
        response: Response,
        namespace: FactorioNamespace,
    ) -> Policy:
        # We format the conversation every N steps to add a context summary to the system prompt
        async with timing_tracker.track_async("format_conversation"):
            formatted_conversation = await self.formatter.format_conversation(
                conversation, namespace
            )
        # We set the new conversation state for external use
        self.set_conversation(formatted_conversation)
        return await self._get_policy(formatted_conversation), None

    @tenacity.retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    @track_timing_async("get_policy")
    async def _get_policy(self, conversation: Conversation):
        async with timing_tracker.track_async("llm_call"):
            messages = self.formatter.to_llm_messages(conversation)
            response = await self.api_factory.acall(
                messages=messages,
                n_samples=1,  # We only need one program per iteration
                temperature=self.generation_params.temperature,
                max_tokens=self.generation_params.max_tokens,
                model=self.generation_params.model,
            )

        async with timing_tracker.track_async("parse_response"):
            policy = parse_response(response)
            if not policy:
                raise Exception("Not a valid Python policy")
            policy.input_conversation = conversation
            return policy

    @track_timing_async("agent_end")
    async def end(self, conversation: Conversation, completion: CompletionResult):
        pass
