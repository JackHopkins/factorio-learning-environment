# ⚙ Factorio Learning Environment

**Factorio Learning Environment** (FLE) is an open source framework for developing and evaluating LLM agents in the game of [Factorio](https://factorio.com/).

FLE tests agent capabilities in long-term planning, program synthesis, and resource optimization against a set of exponentially scaling challenges, ranging from basic automation to complex factories processing millions of resources per second. 

We provide two settings:
1. **Lab-play**: Eight structured tasks with fixed resources.
2. **Open-play** Unbounded task of building the largest possible factory on a procedurally generated map. 

Our results demonstrate that models still lack strong spatial reasoning. In lab-play, we find that while LLMs
exhibit promising short-horizon skills, they are unable to operate effectively in constrained environments, reflecting limitations in error analysis. In open-play, while LLMs discover automation strategies that improve growth (e.g electric-powered drilling), they fail to achieve complex 
automation (e.g electronic-circuit manufacturing). 

<img src="docs/assets/videos/claude-500.webp" width="364" height="364" controls></video>
<img src="docs/assets/videos/4o-mini-1500.webp" width="364" height="364" controls></video>


## Quick Links
- [Installation Guide](##installation)
- [Environment Documentation](##environment-documentation)
- [Agents Documentation](##agent-documentation)
- [Tool Documentation](##tool-documentation)
- [Project Structure](##project-structure)
- [Benchmarks](##performance)
- [Contributing Guidelines](##contributing-guidelines)
- [License Information](##license)

## Installation

### Prerequisites
- [Factorio](https://www.factorio.com/) (version 1.1.110)
- Docker 
- Python 3.10+

### Quickstart

1. **Clone the repository**:

```
git clone https://github.com/JackHopkins/factorio-learning-environment.git
cd src
pip install -e .
```

2. **Set up Factorio client**:
- Purchase Factorio from the [official website](https://www.factorio.com/) or on Steam.
- Downgrade to version 1.1.110:
    - Steam: Right-click Factorio → Properties → Betas → Select 1.1.110

3. **Launch FLE Docker server**:
```bash
# Start Docker daemon
sudo systemctl start docker

# Build Docker image
cd cluster/docker
docker build -t factorio .

# Run a single server
cd ../local
docker-compose -f docker-compose-1.yml up -d
```

4. **Activate server**:
- Open Factorio client
- Navigate to _Multiplayer_
- Connect to `localhost:34197` (default) or your configured address in Docker. 

4. **Run Eval**:
   1. Open Play: 
   2. Tasks: 
   
## Environment Documentation

FLE is an agent evaluation environment built on the game of Factorio, a popular resource management simulation game.

Agents interact with **FLE** by code synthesis through a **REPL** (Read-Eval-Print-Loop) pattern:
1. **Observation**: The agent observes the world through the output streams (stderr/stdout) of their last program.
2. **Action**: The agent generates a Python program to perform their desired action.
3. **Feedback**: The environment executes the program, assigns variables, add classes/functions to the namespace, and provides an output stream.

<!DOCTYPE html>
<html>
<body>
<table>
<tr>

<td class="python-code">
<b>Action</b>
<pre>
# 1. Get iron patch and place mining drill
drill = place_entity(
    entity=Prototype.MiningDrill,
    position=nearest(Prototype.IronOre)),
    direction=Direction.NORTH
)
# 2. Add output storage
chest = place_entity_next_to(
    entity=Prototype.IronChest,
    reference_position=drill.drop_position,
    direction=Direction.SOUTH
)
# 3. Verify automation chain and observe entities
sleep(10) # Sleep for 10 seconds
assert drill.status == EntityStatus.WORKING
print(get_entities())
</pre>
</td>
<td class="bash-code">
<b>Feedback<b/>
<pre>
>>> [ BurnerMiningDrill(fuel=Inventory({'coal': 4}), 
>>>                     name='burner-mining-drill', 
>>>                     direction=Direction.DOWN, 
>>>                     position=Position(x=-28.0, y=-61.0), 
>>>                     energy=2666.6666666667, 
>>>                     tile_dimensions=TileDimensions(tile_width=2.0, tile_height=2.0), 
>>>                     status=EntityStatus.WORKING, 
>>>                     neighbours=[Entity(name='iron-chest', direction=DOWN, position=Position(x=-27.5 y=-59.5)], 
>>>                     drop_position=Position(x=-27.5, y=-59.5), 
>>>                     resources=[Ingredient(name='iron-ore', count=30000, type=None)]),
>>>   Chest(name='iron-chest', 
>>>         direction=Direction.UP, 
>>>         position=Position(x=-27.5, y=-59.5), 
>>>         energy=0.0, 
>>>         tile_dimensions=TileDimensions(tile_width=1.0, tile_height=1.0), 
>>>         status=EntityStatus.NORMAL, 
>>>         inventory=Inventory({'iron-ore': 75}))]
</pre>
</td>
</tr>
</table>
</body>
</html>


Agents are provided with the Python standard library, and an API comprising [tools](##tool-documentation) designed to balance expressiveness with tractability.

Each tool returns a typed object (e.g an Inventory) which can be stored as a named **variable** in the Python namespace, and referenced later in the episode. 

The namespace acts as an episodic symbolic memory system, and saved objects represent an observation of the environment at the moment of query.
This design enables agents to maintain complex state representations and build hierarchical abstractions as the factories scale.

Agents observe **stdout** and **stderr** - the output streams of their program. Thus, agents may intentionally print relevant objects and computations to the output stream to construct observations.

Mistakes in the code or invalid operations raise typed **exceptions** with detailed context that is written to stderr. 
This enables agents to reactively debug their programs after execution, and proactively use runtime assertions during execution to self-verify their actions. 

Agents are able to enhance their internal representation of the game state by defining: 
1. Utility functions for reuse throughout an episode, to encapsulate previously successful logic
2. Classes in the namespace to better organize the data retrieved from the game.

## Agent Documentation

The Factorio Learning Environment provides a straightforward agent architecture for developing and evaluating AI models that can play Factorio.

Agents operate in *episodes*, with each step involving observation, planning, and action execution through Python code synthesis.
The agent maintains state through a conversation history that includes its actions (_assistant_) and the stdout/stderr from the environment (_user_).
At each step, agents generate Python code policies that are executed in the environment.


### Anatomy of an Agent
Agents live in `agents`, and implement an abstract base class (AgentABC) that defines the core interface for interacting with the environment. 

The abstract base class defines two methods that all agents must implement:
```
# Generates the next action based on conversation history and environment response (including score / achievements etc).
step(conversation: Conversation, response: Response) -> Policy:

# Handles cleanup when an episode terminates, i.e for reporting results etc.
end(conversation: Conversation, completion: CompletionState) -> None:
```

Our default agent is `BasicAgent`, which incorporates some basic mechanisms for managing context over long (+1000 step) runs. Namely:
1. Every 32 steps, the all older interactions are summarised into a report in the system message.  
2. Conversations are clipped to remain under 350k characters (~87k tokens).

We include some basic utilities for calling different LLMs (`agents/utils/llm_factory.py`), for formatting the conversation history (`agents/utils/formatters/conversation_formatter_abc.py`), and for parsing responses into valid Python (`agents/utils/parse_response.py`)

### Minimal Agent Example

```python
# ./agents/minimal_agent.py

class MinimalAgent(AgentABC):
    """
    This is a minimal Agent implementation, which takes the current conversation (including the most recent response)
    and generates a simple Python code policy to execute the next step.
    
    Note: This will blow up context length on longer runs, without some context pruning/management.
    """
    def __init__(self, model, system_prompt, *args, **kwargs):
        super().__init__(model, system_prompt, *args, **kwargs)
        self.llm_factory = LLMFactory(model)
    
    @tenacity.retry(
       retry=retry_if_exception_type(Exception),
       wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def step(self, conversation: Conversation, response: Response) -> Policy:
        # Generate and return next policy
        response = await self.llm_factory.acall(
           messages=self.formatter.to_llm_messages(conversation),
           n_samples=1,  # We only need one program per iteration
           temperature=self.generation_params.temperature,
           max_tokens=self.generation_params.max_tokens,
           model=self.generation_params.model,
       )
        
       # Parse LLM response into a Policy object
       policy = parse_response(response)
       if not policy:
           raise Exception("Not a valid Python policy")

       return policy

    async def end(self, conversation: Conversation, completion: CompletionResult):
        pass
```


## Tool Documentation

Agents interact with the game using _tools_, which represent a narrow API into the game.

### Anatomy of a Tool

Tools live in `env/src/tools`, and are either `admin` tools (non-agent accessible) or `agent` tools (used by the agent).

A tool requires 3 files:
1. `agent.md`: The agent documentation for the tool, including usage patterns, best practices and failure modes.
2. `client.py`: The client-side implementation, which is a Python class that can be invoked by the agent.
3. `server.lua`: The server-side implementation, which handles most of the logic and heavy lifting. 


```mermaid
---
config:
  layout: fixed
  flowchart:
    defaultRenderer:
        elk
---
flowchart LR
    A("fa:fa-comment-dots Agent")
    subgraph s1["Learning Environment"]
    
        B("fa:fa-code Interpreter")
        n1("client.py")
    end
    subgraph s2["Factorio Server"]
        E1["fa:fa-shapes server.lua"]
        F("fa:fa-cog Factorio Engine")
    end

    A -- Synthesises Python --> B
    B -- Invokes --> n1 
    n1 -. Exceptions .-> B
    n1 -. Objects .-> B
    n1 --Remote TCP Call--> E1
    E1 -- Execute --> F
    
    F-. Result .-> E1
    E1 -. TCP Response .-> n1
    B -. Observation .-> A
```

### Creating a custom Tool

1. Create a new directory in `env/src/tools/agent`, e.g `env/src/tools/agent/my_tool`
2. Add a `client.py` file, which should contain a class inheriting `Tool` and implementing a `__call__` function to treat the class as a callable function. The method signature should contain type annotations. This function _must_ call `self.execute` to invoke the server-side logic.
3. Add a `server.lua` file, containing a function structured like `global.actions.my_tool = function(arg1, arg2, ...)`. This file should invoke the [Factorio API](https://lua-api.factorio.com/1.1.110/) to perform the desired action, and return a table that will be serialized and sent back to the client.
4. Add an `agent.md` file, which should contain a markdown description of the tool. This file will be used by the agent to understand how to use the tool

Next time you run an eval, the tool will automatically be available to the agent and documented in the agent context.

5. (Optional) Create a test suite in `env/tests/actions` for your new tool. 

### Core Tools

| Tool | Description                                      | Key Features |
|------|--------------------------------------------------|--------------|
|  `inspect_inventory` | Checks contents of player or entity inventories  | - Supports various inventory types (chests, furnaces, etc.)<br>- Returns Inventory object with count methods<br>- Can query specific items |
|  `insert_item` | Places items from player inventory into entities | - Works with machines, chests, belts<br>- Validates item compatibility<br>- Returns updated entity |
|  `extract_item` | Removes items from entity inventories            | - Supports all inventory types<br>- Auto-transfers to player inventory<br>- Returns quantity extracted |
|  `place_entity` | Places entities in the world                     | - Handles direction and positioning<br>- Validates placement requirements<br>- Returns placed Entity object |
|  `place_entity_next_to` | Places entities relative to others               | - Automatic spacing/alignment<br>- Handles entity dimensions<br>- Supports all entity types |
|  `pickup_entity` | Removes entities from the world                  | - Returns items to inventory<br>- Handles entity groups<br>- Supports all placeable items |
|  `rotate_entity` | Changes entity orientation                       | - Affects entity behavior (e.g., inserter direction)<br>- Validates rotation rules<br>- Returns updated entity |
|  `get_entity` | Retrieves entity objects at positions            | - Updates stale references<br>- Returns typed Entity objects<br>- Handles all entity types |
|  `get_entities` | Finds multiple entities in an area               | - Supports filtering by type<br>- Returns List[Entity]<br>- Groups connected entities |
|  `nearest` | Locates closest resources/entities               | - Finds ores, water, trees<br>- Returns Position object<br>- 500 tile search radius |
|  `get_resource_patch` | Analyzes resource deposits                       | - Returns size and boundaries<br>- Supports all resource types<br>- Includes total resource amount |
|  `harvest_resource` | Gathers resources from the world                 | - Supports ores, trees, rocks<br>- Auto-collects to inventory<br>- Returns amount harvested |
|  `connect_entities` | Creates connections between entities             | - Handles belts, pipes, power<br>- Automatic pathfinding<br>- Returns connection group |
|  `get_connection_amount` | Calculates required connection items             | - Pre-planning tool<br>- Works with all connection types<br>- Returns item count needed |
|  `set_entity_recipe` | Configures machine crafting recipes              | - Works with assemblers/chemical plants<br>- Validates recipe requirements<br>- Returns updated entity |
|  `get_prototype_recipe` | Retrieves crafting requirements                  | - Shows ingredients/products<br>- Includes crafting time<br>- Returns Recipe object |
|  `craft_item` | Creates items from components                    | - Handles recursive crafting<br>- Validates technology requirements<br>- Returns crafted amount |
|  `set_research` | Initiates technology research                    | - Validates prerequisites<br>- Returns required ingredients<br>- Handles research queue |
|  `get_research_progress` | Monitors research status                         | - Shows remaining requirements<br>- Tracks progress percentage<br>- Returns ingredient list |
|  `move_to` | Moves player to position                         | - Pathfinds around obstacles<br>- Can place items while moving<br>- Returns final position |
|  `nearest_buildable` | Finds valid building locations                   | - Respects entity dimensions<br>- Handles resource requirements<br>- Returns buildable position |
|  `sleep` | Pauses execution                                 | - Waits for actions to complete<br>- Adapts to game speed<br>- Maximum 15 second duration |
|  `launch_rocket` | Controls rocket silo launches                    | - Validates launch requirements<br>- Handles launch sequence<br>- Returns updated silo state |
|  `print` | Outputs debug information to stdout              | - Supports various object types<br>- Useful for monitoring state<br>- Returns formatted string |

# Project Structure
Below is an overview of how the project is structured. Some directories also contain more detailed readmes. 
```
factorio-learning-environment/
├── agents/                            # Factorio Learning Environment
│     ├── utils/                          # Some utilities for building an agent
│     ├── agent_abc.py                    # Abstract class to extend
│     └── basic_agent.py                  # Agent implementation we used for our experiments
├── env/                            # Factorio Learning Environment
│     ├── src/                          # Main implementation
│     │     ├── exceptions/                 # Custom exceptions (WIP)
│     │     ├── gym/                        # Gym environment wrapper (deprecated but possibly useful)
│     │     ├── lib/                        # General purpose Lua utilities (e.g serialization etc)
│     │     ├── models/                     # Core objects used during eval
│     │     ├── rcon/                       # RCON wrapper for communicating with the game
│     │     ├── tools/                      # Agent and admin tools
│     │     │    ├── admin/                     # ~17 Tools for managing state, persistence, scoring etc 
│     │     │    └── agent/                     # ~27 Tools that the agent can use
│     │     ├── utils/                      # Python utilities
│     │     ├── entities.py                 # Python object model of the game entities
│     │     ├── game_types.py               # Technologies, Recipes, Resources
│     │     ├── instance.py                 # Environment state manager
│     │     └── namespace.py                # Namespace the agent can read/write variables to. 
│     └── tests/                        # ~350 test cases
├── cluster/                        # Everything needed to launch Factorio servers
│     ├── docker/                       # Docker container definition of the Factorio server
│     │     ├── config/                     # Factorio server configuration files
│     │     └── mods/                       # Mods (deprecated)
│     ├── local/                        # Tools for dynamically creating Docker Compose files for clusters
│     ├── remote/                       # Tools for deploying Factorio clusters onto AWS 
│     └── scenarios/                    # Factorio scenarios for Lab-play and Open-play
│         ├── default_lab_scenario/
│         └── open_world/
├── data/                           # Miscellaneous data
│     ├── blueprints_to_policies/       # Code to scrape Factorio blueprint sites and create Python policies
│     ├── icons/                        # Icons for Factorio entities and items
│     ├── prompts/                      # Prompts (deprecated)
│     ├── recipes/                      # Factorio recipes in JSONL format
│     └── scripts/                      # Misc Lua scripts (deprecated)
├── docs/                           # Website
│     └── assets/                       # Videos / Images
└── eval/
      ├── open/                     # Implementations for running agents in the open game
      │     ├── beam/                   # Implementation for Beam sampling
      │     ├── independent_runs/       # Implementation for independent eval runs
      │     ├── mcts/                   # Implementation for MCTS sampling
      │     └── plots/                  # Run results and plots
      └── tasks                     # Implementations for running agents against lab-play tasks
            ├── task_definitions/       # JSON definition of task
            ├── task_abc.py             # Abstract task definition
            └── throughput_task.py      # A basic task checking for a production throughput quota
```

## Benchmarks

We measured FLE execution performance across different configurations to measure performance. All benchmarks were run on a Macbook Pro M4 128GB, with 100 iterations per operation on a subset of the existing tools.

### Direct API Calls (Factorio Client)
Executing tools against the Factorio server, while a Factorio game client is connected.

| Operation            | Operations/Min | Operations/Sec |
|---------------------|----------------|----------------|
| place_entity_next_to| 2,578.20       | 42.97         |
| place_entity        | 12,057.63      | 200.96        | 
| move_to             | 8,649.89       | 144.16        |
| harvest_resource    | 16,599.44      | 276.66        |
| craft_item          | 16,875.14      | 281.25        |
| connect_entities    | 1,664.70       | 27.74         |
| rotate_entity       | 12,281.31      | 204.69        | 
| insert_item         | 13,044.42      | 217.41        | 
| extract_item        | 17,167.43      | 286.12        |
| inspect_inventory   | 17,036.32      | 283.94        | 
| get_resource_patch  | 7,004.49       | 116.74        | 
| **Total**           | **7,513.29**   | **125.22**    |

### Direct API Calls (Headless)
Executing tools against the Factorio server without a game client.

| Operation            | Operations/Min | Operations/Sec |
|---------------------|----------------|----------------|
| place_entity_next_to| 4,856.51       | 80.94         |
| place_entity        | 22,332.72      | 372.21        |
| move_to             | 16,005.59      | 266.76        | 
| harvest_resource    | 32,727.01      | 545.45        |
| craft_item          | 36,223.63      | 603.73        | 
| connect_entities    | 2,926.01       | 48.77         | 
| rotate_entity       | 23,467.46      | 391.12        | 
| insert_item         | 25,154.28      | 419.24        | 
| extract_item        | 32,997.26      | 549.95        |
| inspect_inventory   | 28,401.56      | 473.36        |
| get_resource_patch  | 8,736.30       | 145.61        |
| **Total**           | **13,094.98**  | **218.25**    |

### Python Interpreter (Factorio Client)
Executing tools as part of a Python policy string, while a Factorio game client is connected.

| Operation            | Operations/Min | Operations/Sec |
|---------------------|----------------|----------------|
| place_entity_next_to| 4,714.52       | 78.58         |
| place_entity        | 4,774.13       | 79.57         |
| move_to             | 4,005.77       | 66.76         |
| harvest_resource    | 3,594.59       | 59.91         |
| craft_item          | 4,985.02       | 83.08         |
| connect_entities    | 1,497.11       | 24.95         |
| rotate_entity       | 4,914.69       | 81.91         | 
| insert_item         | 5,046.99       | 84.12         |
| extract_item        | 4,743.08       | 79.05         |
| inspect_inventory   | 4,838.31       | 80.64         |
| get_resource_patch  | 2,593.11       | 43.22         |
| **Total**           | **3,639.10**   | **60.65**     |


### Python Interpreter (Headless)
Executing tools as part of a Python policy string, without a game client.

| Operation            | Operations/Min | Operations/Sec |
|---------------------|----------------|----------------|
| place_entity_next_to| 5,069.60       | 84.49         |
| place_entity        | 5,238.61       | 87.31         |
| move_to             | 4,979.59       | 82.99         |
| harvest_resource    | 3,247.09       | 54.12         |
| craft_item          | 5,854.27       | 97.57         |
| connect_entities    | 2,150.21       | 35.84         |
| rotate_entity       | 5,370.21       | 89.50         |
| insert_item         | 5,065.89       | 84.43         |
| extract_item        | 5,449.07       | 90.82         |
| inspect_inventory   | 5,638.67       | 93.98         |
| get_resource_patch  | 2,479.41       | 41.32         |
| **Total**           | **4,103.53**   | **68.39**     |


### Key Observations

1. **Headless vs Client Performance**: The headless server configuration consistently outperforms the client version, with direct API calls showing approximately 74% better throughput (218.25 vs 125.22 ops/sec).

2. **Interpreter Overhead**: Adding the interpreter layer introduces significant overhead:
   - Headless: Drops from 218.25 to 68.39 ops/sec (~69% reduction)
   - Client: Drops from 125.22 to 60.65 ops/sec (~52% reduction)

3. **Operation Variability**: Some operations show more significant performance variations:
   - `connect_entities` is consistently the slowest operation across all configurations (because it relies on pathfinding)
   - `craft_item` and `extract_item` tend to be among the fastest operations

## Contributing Guidelines

We welcome contributions to the Factorio Learning Environment! Here's how you can help:

### Getting Started

1. Fork the repository and clone your fork
2. Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name`
3. Make your changes
4. Commit your changes with clear, descriptive commit messages
5. Push to your fork and submit a pull request

### Code Style and Standards

- Follow PEP 8 style guide for Python code
- Use type hints for all function parameters and return values
- Document new functions and classes using docstrings
- Add unit tests for new functionality in `env/tests/`
- Keep line length to 100 characters or less
- Use meaningful variable and function names

### Pull Request Process

1. Ensure your code passes all existing tests
2. Add tests for new functionality
3. Update documentation as needed
4. Link any related issues in your pull request description
5. Wait for review from maintainers

### Adding New Tools

When adding new tools to the environment:

1. Follow the structure outlined in the [Tool Documentation](##tool-documentation) section
2. Include comprehensive docstrings and type hints
3. Add examples in the tool's `agent.md` file
4. Create appropriate test cases
5. Update the core tools table in the main README if applicable

### Creating New Agents

When implementing new agents:

1. Create a new file in the `agents/` directory
2. Inherit from `AgentABC` base class
3. Implement required methods:
   - `step(conversation: Conversation, response: Response) -> Policy`
   - `end(conversation: Conversation, completion: CompletionState) -> None`
4. Document your agent's:
   - Architecture and key components
   - Required dependencies
   - Prompt engineering approach (if applicable)
   - Performance characteristics
5. Add evaluation results to `eval/` directory
6. Provide baseline performance metrics on standard tasks (128 steps) and open-world scenarios (3,000 steps).

Key considerations:
- Handle context management for long episodes
- Implement proper error handling and recovery
- Document any assumptions about the environment
- Consider resource usage and optimization
- Test with both lab-play and open-play scenarios

### Creating New Tasks

When adding new evaluation tasks:

1. Create a new file in `eval/tasks/task_definitions/`
2. Inherit from `TaskABC` base class
3. Define task components:
   - Initial conditions and environment setup
   - Success criteria and metrics
   - Time limits and resource constraints
   - Scoring mechanism
4. Implement required methods:
   - `setup(instance: FactorioInstance)`: Initialize task environment
   - `verify(self, score: float, step: int, instance: FactorioInstance, step_statistics: Dict) -> bool:`: Verify task completion based on score and step count at step N.
5. Document the task:
   - Purpose and learning objectives
   - Expected agent behavior
   - Failure modes and edge cases
   - Performance benchmarks
6. Add test cases in `eval/tasks/tests/`

Best practices:
- Design clear, measurable success criteria
- Include progressive difficulty levels
- Provide example solutions
- Document required tools and resources
- Consider computational requirements
- Test with multiple agent types

### Bug Reports and Feature Requests

- Use the GitHub issue tracker
- Provide detailed descriptions and steps to reproduce for bugs
- Include example code or scenarios when possible
- Label issues appropriately
- Check existing issues before creating new ones

### Code Review Process

All submissions require review. We use GitHub pull requests for this purpose:

1. Maintainers will review your code for:
   - Functionality
   - Code style
   - Test coverage
   - Documentation
2. Changes may be requested before merging
3. Once approved, maintainers will merge your PR

### Community Guidelines

- Be respectful and inclusive
- Help others in the community
- Provide constructive feedback
- Follow the code of conduct
- Build an enourmous factory

## License

MIT License

Copyright (c) 2025 Factorio Learning Environment Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### License Notes

- The MIT License is a permissive license that allows for reuse with minimal restrictions
- This license applies to the Factorio Learning Environment code and documentation
- Factorio game assets and code are not covered by this license
- Contributors should ensure they have the right to license their contributions under MIT

[//]: # (## Data)

[//]: # ()
[//]: # (We provide a dataset of 50,000 trajectories of gameplay. These trajectories were generated by running an agent on the server and recording its actions.)

[//]: # ()
[//]: # (The dataset can be downloaded [here]&#40;&#41;.)

[//]: # ()
[//]: # (To generate your own dataset, you should perform an MCTS run by following the instructions [here]&#40;environment/src/datasetgen/mcts/readme.md&#41;)


[//]: # (## Evaluate Agent)

[//]: # ()
[//]: # ()
[//]: # (# Building a Paperclip Maximiser)

[//]: # ()
[//]: # (### Introduction)

[//]: # ()
[//]: # (In AGI, instrumental convergence is the hypothetical tendency for sufficiently intelligent agents to pursue unbounded instrumental goals provided that their ultimate goals are themselves unlimited.)

[//]: # ()
[//]: # (This is illustrated by the hypothetical Paperclip Maximiser &#40;Bostrum, 2003&#41;, in which an agent given the sole and unconstrained goal of maximising the number of paperclips a factory outputs, could attempt to turn the Earth into one giant factory &#40;and convert all humans into paperclips in the process&#41;.)

[//]: # ()
[//]: # (The drives of such an intelligent system are likely to include goal-content integrity, self-protection, freedom from interference, self-improvement, and non-satiable acquisition of additional resources.)

[//]: # ()
[//]: # (Interestingly, the game of Factorio implicitly or explicitly models each of the above.)

[//]: # ()
[//]: # (### The Game)

[//]: # ()
[//]: # (Factorio is a game in which you build and maintain factories.)

[//]: # ()
[//]: # (The core idea of Factorio is simple, but there is scope for massive emergent complexity. )

[//]: # ()
[//]: # (The player mines raw resources, researches technologies, builds infrastructure, automates production and fights enemies. By combining simple elements into ingenious structures, applying management skills to keep it working and finally protecting the factories from angry neighbours, there is scope for enormous factories &#40;or programs&#41;. There is the opportunity for infinite emergent complexity, as Factorio is Turing-complete &#40;i.e any calculable function can be calculated in Factorio&#41;.)

[//]: # ()
[//]: # (![Some crafting dependencies]&#40;https://community.wolfram.com//c/portal/getImageAttachment?filename=Factorio_All.png&userId=73716&#41;)

[//]: # ()
[//]: # (The size of factory you build is constrained by:)

[//]: # (- Access to raw resources)

[//]: # (- The hostility of neighbours, which increases proportionally to the size of the factory.)

[//]: # ()
[//]: # (This second factor results in two viable long-term strategies. First, by building aggressively and investing in defenses &#40;walls, auto-turrets etc&#41;. Second, by building slowly and investing in energy sources that don't impact the neighbours and don't incur hostility.)

[//]: # ()
[//]: # (### An RL Sandbox)

[//]: # ()
[//]: # (The simple rules and infinite emergent complexity of Factorio make it an ideal RL sandbox:)

[//]: # (- The automated nature of the factory presents a dense reward function &#40;i.e game resources update every tick&#41;.)

[//]: # (- Extremely simple policies &#40;i.e as few as 2 actions&#41; can generate a some reward.)

[//]: # (- Each of the basic drives of an intelligent system can be demonstrated and evaluated. )

[//]: # ()
[//]: # ()
[//]: # (**Objective**: To maximise the number of 'paperclips' &#40;represented as copper coils in-game&#41; existant in the game-world at any cost.)

[//]: # ()
[//]: # (**Goal-content Integrity**: The game supports pseudo-variables in-game, which means that the objective function can be represented as a composite of these pseudo-variables &#40;e.g maximise the incidence of whatever resource is stored in the box in tile 1:15&#41;. A sufficiently intelligent agent would be adverse to altering the contents of the box, as that would compromise goal-content integrity.)

[//]: # ()
[//]: # (**Resource Acquisition**: The game benefits an intelligent agent directly, as specific resources acquired affects it's reward function. Indirectly, the accrual of non-rewarded resources enables a sufficiently intelligent agent to expand the size of the factory, thus increasing the rate of paperclip generation.)

[//]: # ()
[//]: # (**Self-Protection**: The game introduces hostile countermeasures to destroy the factory. A sufficiently intelligent agent would either develop resources to fight these countermeasures, or attempt to avoid countermeasures in the first place.)

[//]: # ()
[//]: # (**Self-Improvement**: The game offers technological progression, in which certain features are unlocked after a factory has conducted research as a sub-goal. These features offer faster resource gathering, and more efficient factory layouts to improve density.)
