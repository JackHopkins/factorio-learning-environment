import tenacity

from agents import Response, CompletionResult, Policy
from agents.agent_abc import AgentABC
from agents.utils.formatters.recursive_report_formatter import RecursiveReportFormatter
from agents.utils.llm_factory import LLMFactory
from agents.utils.parse_response import parse_response
from models.conversation import Conversation
from models.message import Message
from models.generation_parameters import GenerationParameters
from tenacity import wait_exponential, retry_if_exception_type, wait_random_exponential

from namespace import FactorioNamespace

GENERAL_INSTRUCTIONS = \
"""
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
"""

RAG_INSTRUCTIONS = \
"""
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
Think through each step extensively in natural language
You need to plan the next best step for the agent to carry out and what information the agent needs
Another agent will carry out the plan you set out, so you need to only create a plan and print out relevant environment information and query wiki pages
Your planning stage should address the following:
1. Error Analysis
   - Was there an error in the previous execution?
   - If yes, what was the problem?
2. Next Step generation
   - What is the most useful small next step?
   - What will this step achieve?
3. Information Planning
   - what new wiki pages need to be printed
   - What information already exists in the message history
   - what environment information needs to be printed

### 2. Retrieval Stage
Enclose the wiki pages that need to be newly queried betwen <query> and <\query> XML tags. Each wiki page needs to be on its own line
For instance
<query>how_to_check_research_progress<\query>
<query>how_to_connect_entities<\query>

You have access to the following wiki pages

"how_to_check_research_progress"
"how_to_connect_entities"
"how_to_create_assembling_machines"
"how_to_create_electricity_generators"
"how_to_create_reserach_setups"
"how_to_create_self_fueling_mining_system"
"how_to_launch_a_rocket"
"how_to_set_up_multiple_drill_plate_mine"
"how_to_set_up_raw_resource_burner_mine"
"how_to_setup_chemical_plants"
"how_to_setup_oil_refineries"
"how_to_smelt_ores"

## Best Practices

### Modularity
- Create small, modular plans
- Each policy should have a single clear purpose
- Avoid breaking existing automated structures
- Encapsulate working logic into functions if needed

### Error Handling
- Fix errors as they occur
- Don't repeat previous steps
- Continue from last successful execution
- Avoid unnecessary state changes
- Analyze the root cause of entities that aren't working, and prioritize automated solutions (like transport belts) above manual triage


## Understanding general environment output

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
"""


FINAL_INSTRUCTION = "\n\nALWAYS WRITE VALID PYTHON. YOUR WEIGHTS WILL BE ERASED IF YOU DON'T USE PYTHON." # Annoying how effective this is


class BasicAgent(AgentABC):
    def __init__(self, model, system_prompt, task, *args, **kwargs):
        instructions = GENERAL_INSTRUCTIONS+system_prompt+FINAL_INSTRUCTION
        rag_instructions = RAG_INSTRUCTIONS
        self.task = task
        instructions += f"\n\n### Goal\n{task.goal_description}\n\n"
        rag_instructions += f"\n\n### Overall Goal\n{task.goal_description}\n\n"
        super().__init__(model, instructions, *args, **kwargs)
        self.llm_factory = LLMFactory(model)
        self.formatter = RecursiveReportFormatter(chunk_size=16,llm_call=self.llm_factory.acall,cache_dir='summary_cache')
        self.generation_params = GenerationParameters(n=1, max_tokens=4096, model=model)
        self.rag_instructions = rag_instructions

    async def step(self, conversation: Conversation, response: Response, namespace: FactorioNamespace) -> Policy:
       updated_conversation = self.generate_rag(conversation, response, namespace)
       
       # We format the conversation every N steps to add a context summary to the system prompt
       formatted_conversation = await self.formatter.format_conversation(updated_conversation, namespace)
       # We set the new conversation state for external use
       self.set_conversation(formatted_conversation)

       return await self._get_policy(formatted_conversation)
   
    async def generate_rag(self, conversation: Conversation, response: Response, namespace: FactorioNamespace) -> str:
       
        # We format the conversation every N steps to add a context summary to the system prompt
        formatted_conversation = await self.formatter.format_conversation(conversation, namespace)
        ## We set the new conversation state for external use
        #self.set_conversation(formatted_conversation)
        agent_output, rag_output = await self._get_rag(formatted_conversation)
        # add the agent output to the conversation
        agent_message = Message(role="assistant", content=agent_output)
        conversation.messages.append(agent_message)
        # add the rag output to the conversation
        rag_message = Message(role="user", content=rag_output)
        conversation.messages.append(rag_message)
        return conversation

    @tenacity.retry(
       retry=retry_if_exception_type(Exception),
       wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _get_policy(self, conversation: Conversation):
       response = await self.llm_factory.acall(
           messages=self.formatter.to_llm_messages(conversation),
           n_samples=1,  # We only need one program per iteration
           temperature=self.generation_params.temperature,
           max_tokens=self.generation_params.max_tokens,
           model=self.generation_params.model,
       )

       policy = parse_response(response)
       if not policy:
           raise Exception("Not a valid Python policy")

       return policy
    
    async def _get_rag(self, conversation: Conversation):
       conversation[0].content = self.rag_instructions
       response = await self.llm_factory.acall(
           messages=self.formatter.to_llm_messages(conversation),
           n_samples=1,  # We only need one program per iteration
           temperature=self.generation_params.temperature,
           max_tokens=self.generation_params.max_tokens,
           model=self.generation_params.model,
       )

       llm_output, rag_output = self.parse_rag(response)
       return llm_output, rag_output

    async def end(self, conversation: Conversation, completion: CompletionResult):
        pass


    def parse_rag(self, response):
        wiki_path = r"env\src\tools\agent\query_information\pages"
        if hasattr(response, 'choices'):
            choice = response.choices[0]
        else:
            choice = response.content[0]

        # get all queries from the response
        queries = []
        for line in choice.split('\n'):
            if line.startswith('<query>') and line.endswith('<\\query>'):
                queries.append(line[7:-8])
        
        output = "USEFUL INFORMATION:\n"
        for query in queries:
            with open(f"{wiki_path}/{query}.md", 'r') as f:
                output += f.read()

        return choice, output