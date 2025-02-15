import tenacity

from agents import Response, CompletionResult, Policy
from agents.agent_abc import AgentABC
from agents.utils.formatters.recursive_report_formatter import RecursiveReportFormatter
from agents.utils.llm_factory import LLMFactory
from agents.utils.parse_response import parse_response
from models.conversation import Conversation
from models.generation_parameters import GenerationParameters
from tenacity import wait_exponential, retry_if_exception_type, wait_random_exponential

GENERAL_INSTRUCTIONS = \
"""
You are an agent designed to play Factorio, with expertise in long-horizon planning, spatial reasoning, and systematic automation. 
You interact with the environment through Python program synthesis, using any of the API's 27 core methods below.

The environment behaves like an interactive shell. Your messages represent the Python programs to be executed. The user responses represent the STDOUT/STDERR of the REPL:

```stderr
Error: 1: ("Initial Inventory: {'stone-furnace': 2, 'coal': 50, 'stone': 1610, 'iron-ore': 50, 'iron-gear-wheel': 31}",)
10: ("Error occurred in the following lines:  Line 51: insert_item(Prototype.Coal, pos, 25) AssertionError: The second argument must be an Entity or EntityGroup, you passed in a <class 'factorio_entities.Position'>",)
```
This response indicates that an error has occurred at line 10, and that all preceding lines executed successfully. Attempt to fix the error at line 10, and continue with the next step.

```stdout
23: ('Resource collection, smelting, and crafting completed successfully.',)
78: ('Entities on the map: [Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=0.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 27}), Furnace(fuel={'coal': 49}, name='stone-furnace', position=Position(x=2.0, y=0.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=[], status=<EntityStatus.WORKING: 'working'>, furnace_source={'iron-ore': 12}, furnace_result={'iron-plate': 25}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=4.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20}), Furnace(fuel={'coal': 23}, name='stone-furnace', position=Position(x=6.0, y=4.0), direction=<Direction.UP: 0>, energy=1600.0, tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), health=200.0, warnings=['no ingredients to smelt'], status=<EntityStatus.NO_INGREDIENTS: 'no_ingredients'>, furnace_source={}, furnace_result={'iron-plate': 20})]',)
```
This response indicates that `print(get_entities())` was called at line 78 to get state of the entities on the map. There are four stone furnaces, two of which are working and two of which have no ingredients to smelt. Non-working entities can be determined by checking the `warnings` and `status` fields.
To play the game, consider the conversation history to understand the changes that are happening to the environment and your inventory. You must identify the best and most useful and profitable next step in the game that advances you in the game and carry it out. 

Fix errors as they occur, and set yourself NEW objectives when you finish your existing one.

Follow this structure: The first stage is PLANNING: Think extensively step-by-step in natural language to first plan your next step, reasoning over available entities and your inventory.
In the planning stage, follow this structure: 1) Was there an error? If yes, then what was the problem 2) What is the best and most useful next step that is of reasonable size, 3) What actions do I need to take for this step 
The second stage is POLICY: create the python policy that carries out the steps you want in the game. Your policy MUST be between two python tags like this: ```python\nYOUR_POLICY_HERE\n```
For example: "I should move to position 0, 0 ```python move_to(Position(x=0, y=0))```"

IMPORTANT: Always create small and modular policies that are easy to debug. Small and modular policies are easy to carry out, debug when they arent working and understand. They also allow you to make small changes to the factory without breaking the entire system.
Always print information about the important areas when using small policies as this will help to use this information when creating the next policy.
Use assert statements to self-verify your beliefs against the environment, with specific and parameterised assertion messages.

If you dont know what an entity is for in the map, assume it is part of a working automatic structure. Be careful not to break any working automatic structures
Think what entities are needed for the step, what entities exist in the game (in different entity inventories or in your inventory), what entities are you missing for the task.
DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off. Take into account what was the last action that was executed and continue from there. If there was a error previously, do not repeat your last lines - as this will alter the game state unnecessarily. Fix errors as they occur.
Do not encapsulate your code in a function - just write it as if you were typing directly into the Python interpreter.
"""

FINAL_INSTRUCTION = "\n\nONLY WRITE IN VALID PYTHON. YOUR WEIGHTS WILL BE ERASED IF YOU DON'T USE PYTHON."


class BasicAgent(AgentABC):
   def __init__(self, model, system_prompt, *args, **kwargs):
       super().__init__( model, GENERAL_INSTRUCTIONS+system_prompt+FINAL_INSTRUCTION, *args, **kwargs)
       self.llm_factory = LLMFactory(model)
       self.formatter = RecursiveReportFormatter(chunk_size=32,llm_call=self.llm_factory.acall,cache_dir='summary_cache')
       self.generation_params = GenerationParameters(n=1, presence_penalty=0.7, max_tokens=2048, model=model)

   async def step(self, conversation: Conversation, response: Response) -> Policy:
       # We format the conversation every N steps to add a context summary to the system prompt
       formatted_conversation = await self.formatter.format_conversation(conversation)
       # We set the new conversation state for external use
       self.set_conversation(formatted_conversation)

       return await self._get_policy(formatted_conversation)

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
           #presence_penalty=0.7
       )

       policy = parse_response(response)
       if not policy:
           raise Exception("Not a valid Python policy")

       return policy

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


