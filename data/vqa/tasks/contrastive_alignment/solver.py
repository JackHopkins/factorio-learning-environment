import json
import re
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from data.vqa.templates import Templates


@solver
def generate_blueprint_title_and_purpose(num_variations: int = 3) -> Solver:
    """Generate multiple title and purpose descriptions for blueprints in a single LLM call.

    Args:
        num_variations: Number of different title/purpose pairs to generate (default: 3)
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})

        # Generate prompt requesting multiple variations at once
        blueprint_copy = blueprint.copy()
        if "label" in blueprint_copy:
            del blueprint_copy["label"]

        prompt = f"""Analyze this Factorio blueprint and generate {num_variations} different metadata variations.

Blueprint:
{json.dumps(blueprint_copy, indent=2)}

Generate {num_variations} different variations, each with:
1. A concise title (max 10 words) that describes what this blueprint builds
2. A purpose description (1-2 sentences) explaining what it does and how it's used

Important guidelines:
- Each variation should emphasize different aspects of the blueprint
- Variation 1: Focus on the primary function and most obvious use case
- Variation 2: Highlight efficiency, automation, or technical aspects
- Variation 3: Emphasize scalability, integration, or advanced features
{f"- Additional variations: Consider alternative use cases, specialized applications, or unique benefits" if num_variations > 3 else ""}

Make each title and purpose distinct while still being accurate.

Format your response as JSON:
```json
{{
    "variations": [
        {{
            "title": "...",
            "purpose": "..."
        }},
        {{
            "title": "...",
            "purpose": "..."
        }},
        ...
    ]
}}
```"""

        state.messages[-1] = ChatMessageUser(content=prompt)
        response = await generate(state)
        completion = response.output.completion

        pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(pattern, completion, re.DOTALL)

        all_titles = []
        all_purposes = []

        if match:
            json_content = match.group(1)
            try:
                data = json.loads(json_content)
                variations = data.get('variations', [])

                for variation in variations:
                    all_titles.append(variation.get('title', ''))
                    all_purposes.append(variation.get('purpose', ''))
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                # Fallback to empty lists
                pass

        # Store all variations
        state.metadata["titles"] = all_titles
        state.metadata["purposes"] = all_purposes

        # Keep single title/purpose for backward compatibility
        if all_titles:
            state.metadata["title"] = all_titles[0]
            state.metadata["purpose"] = all_purposes[0]

        return state

    return solve


@solver
def contrastive_matching(num_options: int = 4) -> Solver:
    """Generate contrastive matching questions for blueprint identification."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})

        # Generate title and purpose for current blueprint if not already done
        if "titles" not in state.metadata or "purposes" not in state.metadata:
            title_purpose_solver = generate_blueprint_title_and_purpose()
            state = await title_purpose_solver(state, generate)

        # Use the first variation for this matching question
        correct_title = state.metadata.get("title", "Unknown Blueprint")
        correct_purpose = state.metadata.get("purpose", "No description available")

        # Create options list (placeholder - in real implementation, would get from other blueprints)
        options = [
            {"title": correct_title, "purpose": correct_purpose}
        ]

        # Add dummy options for now (in real implementation, would sample from other blueprints)
        dummy_options = [
            {"title": "Belt Balancer", "purpose": "Distributes items evenly across multiple belt lanes"},
            {"title": "Train Station", "purpose": "Automated loading and unloading point for trains"},
            {"title": "Power Plant", "purpose": "Generates electricity using steam engines and boilers"}
        ]

        for i in range(min(num_options - 1, len(dummy_options))):
            options.append(dummy_options[i])

        # Shuffle options (keep track of correct answer)
        import random
        correct_index = 0
        random.shuffle(options)

        # Find new position of correct answer
        for i, option in enumerate(options):
            if option["title"] == correct_title:
                correct_index = i
                break

        # Generate matching prompt
        prompt = Templates.contrastive_matching(options=options)

        state.messages = [ChatMessageUser(content=prompt)]
        state.metadata["contrastive_options"] = options
        state.metadata["correct_answer"] = correct_index + 1  # 1-indexed

        return state

    return solve