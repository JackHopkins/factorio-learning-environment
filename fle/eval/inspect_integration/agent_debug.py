"""Debug agent to confirm our custom agent is being called."""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.agent import agent, AgentState
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, get_model
from inspect_ai.scorer import scorer, Score, Target, Scorer, accuracy

import logging

logger = logging.getLogger(__name__)


@task
def agent_debug_test():
    """Debug test to confirm agent execution"""
    return Task(
        dataset=[Sample(input="Debug test input", target="success", id="debug_agent")],
        solver=debug_agent(),  # Use agent as solver
        scorer=debug_scorer(),
    )


@agent
def debug_agent():
    """Debug agent to confirm it gets called"""

    async def execute(state: AgentState) -> AgentState:
        logger.info("🔧 DEBUG: Custom agent execute() method called!")
        logger.info(f"🔧 DEBUG: Initial messages: {len(state.messages)}")

        # Add system message
        system_prompt = """You are a Factorio automation expert. You control the game using Python code with the FLE API.

Your responses must include Python code blocks like this:
```python
# Your FLE API code here
move_to(Position(x=10, y=10))
```

Always include working Python code in your responses."""

        # Replace messages with proper system prompt
        original_input = state.messages[0].content if state.messages else "Debug test"

        state.messages = [
            ChatMessageSystem(content=system_prompt),
            ChatMessageUser(
                content=f"{original_input}\n\nNow write Python code using the FLE API."
            ),
        ]

        logger.info(f"🔧 DEBUG: Set system prompt, now {len(state.messages)} messages")

        # Generate response using Inspect model
        state.output = await get_model().generate(
            input=state.messages, config={"max_tokens": 500, "temperature": 0.1}
        )

        # Add response to conversation
        state.messages.append(state.output.message)

        logger.info(
            f"🔧 DEBUG: Generated response: {len(state.output.completion)} chars"
        )
        logger.info(f"🔧 DEBUG: Final messages: {len(state.messages)}")

        return state

    return execute


@scorer(metrics=[accuracy()])
def debug_scorer() -> Scorer:
    """Debug scorer"""

    async def score(state: AgentState, target: Target) -> Score:
        has_python_code = (
            "```python" in state.output.completion if state.output else False
        )
        logger.info(f"🔧 DEBUG: Response contains Python code: {has_python_code}")

        return Score(
            value=has_python_code,
            answer="success" if has_python_code else "failure",
            explanation=f"Python code found: {has_python_code}",
        )

    return score
