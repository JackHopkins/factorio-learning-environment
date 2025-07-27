import json
import random
from typing import List, Dict, Any
from inspect_ai import task, Task
from inspect_ai.model import ChatMessageUser, ChatMessageTool
from inspect_ai.solver import Solver, solver, TaskState, Generate
from inspect_ai.tool import tool, ToolError
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.solver import system_message, use_tools
from inspect_ai.util import sandbox

from fle.agents.data.screenshots_from_run import create_factorio_instance
from fle.commons.models.rendered_image import RenderedImage
from ...dataset import raw_blueprint_dataset
from ...templates import Templates


@tool
def analyze_blueprint() -> str:
    """
    Analyze a Factorio blueprint using Python code to generate spatial reasoning QA pairs.

    Args:
        code: Python code that analyzes the blueprint and generates qa_pairs

    Returns:
        JSON string containing the generated QA pairs
    """

    async def execute(code: str) -> str:
        # Write the Python code to a file
        await sandbox().write_file("/tmp/analyze.py", code)

        # Execute the code
        result = await sandbox().exec(["python3", "/tmp/analyze.py"])

        if result.success:
            return result.stdout
        else:
            raise ToolError(f"Python execution failed: {result.stderr}")

    return execute


@solver
def generate_spatial_reasoning_with_code(questions_per_blueprint: int = 3) -> Solver:
    """
    Generate spatial reasoning questions using Python code written by the agent.
    """
    instance = create_factorio_instance()
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        entities = blueprint.get("entities", [])

        image: RenderedImage = instance.namespace._render(blueprint=blueprint)
        id = str(hash(str(blueprint)))
        image.save(f"../../images/{id}.jpg")
        state.metadata["image"] = id

        if len(entities) < 2:
            state.metadata["error"] = "Not enough entities for spatial reasoning"
            state.metadata["spatial_questions"] = []
            return state

        # First, write the blueprint data to a file that the code can import
        blueprint_data = f"blueprint = {json.dumps(blueprint, indent=2)}"
        await sandbox().write_file("/tmp/blueprint_data.py", blueprint_data)

        # Create the prompt
        prompt = f"""I need you to analyze a Factorio blueprint and generate {questions_per_blueprint} spatial reasoning QA pairs.

The blueprint has {len(entities)} entities. I've saved the blueprint data to `/tmp/blueprint_data.py`.

Write Python code that:
1. Imports the blueprint data using: `from blueprint_data import blueprint`
2. Analyzes spatial relationships between entities
3. Generates diverse spatial reasoning questions
4. Prints the qa_pairs as JSON

Your code should generate questions about:
- Distances between entities (Manhattan, Euclidean)
- Relative directions (north/south/east/west)
- Spatial patterns (lines, grids, clusters)
- Nearest/farthest entities
- Entities within a certain radius

The output should be a JSON list of QA pairs, each with:
- 'question': The spatial reasoning question
- 'answer': The correct answer
- 'metadata': Additional context about the spatial relationship

Example code structure:
```python
import json
import random
import math
from blueprint_data import blueprint

entities = blueprint.get('entities', [])
qa_pairs = []

# Generate distance questions
for _ in range(2):
    if len(entities) >= 2:
        e1, e2 = random.sample(entities, 2)
        x1, y1 = e1['position']['x'], e1['position']['y']
        x2, y2 = e2['position']['x'], e2['position']['y']

        manhattan = abs(x2 - x1) + abs(y2 - y1)

        qa_pairs.append({{
        'question': f"What is the Manhattan distance between the {{e1['name']}} at ({{x1}}, {{y1}}) and the {{e2['name']}} at ({{x2}}, {{y2}})?",
            'answer': str(manhattan),
            'metadata': {{
        'type': 'distance',
                'entities': [e1['name'], e2['name']],
                'positions': [(x1, y1), (x2, y2)]
            }}
        }})

# Add more question types...

print(json.dumps(qa_pairs, indent=2))
```

Use the analyze_blueprint tool to execute your code."""

        state.messages = [ChatMessageUser(content=prompt)]

        # Let the agent generate and execute code
        state = await generate(state)

        # Extract results from tool calls
        qa_pairs = []
        for tool_call in reversed(state.messages):
            if isinstance(tool_call, ChatMessageTool):
                try:
                    qa_pairs = json.loads(tool_call.content)
                    break
                except json.JSONDecodeError:
                    continue

        state.metadata["spatial_questions"] = qa_pairs
        state.metadata["generation_method"] = "sandbox_code"

        return state

    return solve


@solver
def generate_spatial_context_with_code() -> Solver:
    """
    Generate spatial context questions for denoising scenarios using sandbox Python execution.
    """
    instance = create_factorio_instance()
    async def solve(state: TaskState, generate: Generate) -> TaskState:

        qa_pairs = state.metadata.get("qa_pairs", [])
        if not qa_pairs:
            state.metadata["error"] = "No denoising QA pairs found"
            return state

        core_qa_pairs = []
        images = []
        for pair in qa_pairs:
            core_pair = {}
            for key, value in pair.items():
                if key != "image":
                    core_pair[key] = value
                else:
                    images.append(value)
            core_qa_pairs.append(core_pair)

        # Write the QA pairs data to a file
        qa_data = f"qa_pairs = {json.dumps(core_qa_pairs, indent=2)}"
        await sandbox().write_file("/tmp/qa_pairs_data.py", qa_data)

        prompt = f"""I need you to enhance {len(qa_pairs)} denoising QA pairs with spatial context analysis.

The QA pairs data has been saved to `/tmp/qa_pairs_data.py`. Each pair contains:
- 'removed_entity': The entity that was removed
- 'modified_blueprint': The blueprint after removal
- 'position': Where the entity was removed

Write Python code that:
1. Imports the data: `from qa_pairs_data import qa_pairs`
2. For each QA pair, analyzes nearby entities in the modified blueprint
3. Generates spatial context questions about what's missing
4. Creates enhanced QA pairs with spatial reasoning

Generate questions like:
- "What entity is missing 2 tiles north of the [entity_name] at position ([x], [y])?"
- "An entity was removed between two [entity_type]. What was it?"
- "What's missing from the center of the 3x3 grid?"

Output format should be a JSON list of enhanced QA pairs with:
- All original fields
- 'spatial_question': A context-aware question
- 'nearby_entities': List of nearby entities with distances and directions

Only print the final output to stdout, and nothing else.

Example approach:
```python
import json
from qa_pairs_data import qa_pairs

def get_direction(from_pos, to_pos):
    dx = to_pos['x'] - from_pos['x']
    dy = to_pos['y'] - from_pos['y']

    if abs(dx) > abs(dy):
        return 'east' if dx > 0 else 'west'
    else:
        return 'south' if dy > 0 else 'north'

enhanced_pairs = []

for qa in qa_pairs:
    removed_pos = qa['position']
    entities = qa['modified_blueprint']['entities']

    # Find nearby entities
    nearby = []
    for entity in entities:
        pos = entity['position']
        dist = abs(pos['x'] - removed_pos['x']) + abs(pos['y'] - removed_pos['y'])
        if dist <= 5:
            nearby.append({{
                'name': entity['name'],
                'distance': dist,
                'direction': get_direction(removed_pos, pos)
            }})

    nearby.sort(key=lambda x: x['distance'])

    # Create spatial question
    if nearby:
        nearest = nearby[0]
        spatial_q = f"What entity is missing {{nearest['distance']}} tiles {{nearest['direction']}} of the {{nearest['name']}}?"
    else:
        spatial_q = f"What entity was at position ({{removed_pos['x']}}, {{removed_pos['y']}})?"

    enhanced = qa.copy()
    enhanced['spatial_question'] = spatial_q
    enhanced['nearby_entities'] = nearby[:3]
    enhanced_pairs.append(enhanced)

print(json.dumps(enhanced_pairs, indent=2))
```"""

        state.messages = [ChatMessageUser(content=prompt)]

        # Let the agent generate and execute code
        state = await generate(state)

        # Extract results from tool calls
        for tool_call in reversed(state.messages):
            if isinstance(tool_call, ChatMessageTool):
                try:
                    enhanced_pairs = json.loads(tool_call.content)
                    state.metadata["qa_pairs"] = enhanced_pairs
                    state.metadata["spatial_context_added"] = True
                    break
                except json.JSONDecodeError:
                    continue

        blueprint = state.metadata.get("blueprint", {})
        image: RenderedImage = instance.namespace._render(blueprint=blueprint)
        id = str(hash(str(blueprint)))
        image.save(f"../../images/{id}.jpg")
        state.metadata["image"] = id

        return state

    return solve