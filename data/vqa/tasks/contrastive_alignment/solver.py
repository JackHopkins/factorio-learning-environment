import json
import re
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Solver, solver, TaskState, Generate
from data.vqa.templates import Templates


@solver
def generate_blueprint_title_and_purpose() -> Solver:
    """Generate both title and purpose description for blueprints."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})

        # Generate prompt using Jinja2 template
        del blueprint["label"]
        prompt = Templates.blueprint_title_purpose(blueprint=blueprint)

        state.messages[-1] = ChatMessageUser(content=prompt)

        response = await generate(state)

        completion = response.output.completion

        pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(pattern, completion, re.DOTALL)
        if match:
            json_content = match.group(1)
            data = json.loads(json_content)
            title = data.get('title')
            purpose = data.get('purpose')

            state.metadata["title"] = title
            state.metadata["purpose"] = purpose

        return state

    return solve


@solver
def contrastive_matching(num_options: int = 4) -> Solver:
    """Generate contrastive matching questions for blueprint identification."""
    
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        blueprint = state.metadata.get("blueprint", {})
        
        # Generate title and purpose for current blueprint if not already done
        if "title" not in state.metadata or "purpose" not in state.metadata:
            title_purpose_solver = generate_blueprint_title_and_purpose()
            state = await title_purpose_solver(state, generate)
        
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