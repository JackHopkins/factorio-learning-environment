import asyncio
from typing import List
import re

from fle.agents.llm.api_factory import APIFactory


class ObjectiveTreeSampler:
    def __init__(self, api_factory):
        self.llm = api_factory
        self.indent_pattern = re.compile(r"^(\s*)")

    def _get_indent_level(self, line: str) -> int:
        """Calculate indent level based on spaces before content."""
        if not line:
            return 0
        if not line.strip():
            return 0
        match = self.indent_pattern.match(line)
        return len(match.group(1)) // 3 if match else 0

    def _format_conversation(self, objectives: List[str]) -> str:
        """Format objectives into a conversation string."""
        return "\n".join(objectives)

    def _is_terminal_state(self, response: str) -> bool:
        """Check if the LLM response indicates we should stop expanding this branch."""
        return response.strip() == "</>" or not response.strip()

    async def sample_tree(self, initial_objectives: List[str], number=-1) -> List[str]:
        """
        Sample a complete tree of objectives using depth-first search.

        Args:
            initial_objective: The root objective to start from

        Returns:
            List of objectives forming a complete tree
        """
        initial_count = len(initial_objectives)
        objectives = initial_objectives
        stack = []
        if not initial_objectives:
            stack = [(0, None)]

        for index, objective in enumerate(initial_objectives):
            stack.append((index, objective))  # (index, objective)

        while stack and (number == -1 or len(objectives) < number + initial_count):
            current_idx, current_obj = stack[-1]

            if current_obj:
                # Format current state of objectives for the LLM
                conversation = self._format_conversation(objectives + ["<>"])
            else:
                # Format current state of objectives for the LLM
                conversation = self._format_conversation(["<>"])
                objectives = objectives[1:]
                stack.pop()  # Backtrack

            # Get next objective from LLM
            response = await self._get_objective(conversation)

            if self._is_terminal_state(response):
                stack.pop()  # Backtrack
                continue

            print(response)

            # Add new objective to our list
            insert_idx = current_idx + 1
            for i in range(current_idx + 1, len(objectives)):
                if self._get_indent_level(objectives[i]) <= self._get_indent_level(
                    current_obj
                ):
                    break
                insert_idx = i + 1

            objectives.insert(insert_idx, response)
            stack.append((insert_idx, response))

        return objectives

    async def _get_objective(self, conversation: str) -> str:
        """Get next objective from LLM."""
        response = await self.llm.acall(
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a helpful assistant that decides on the most appropriate Factorio game objective",
                        }
                    ],
                },
                {"role": "user", "content": [{"type": "text", "text": conversation}]},
            ],
            n_samples=1,
            temperature=0.3,
            max_tokens=128,
            logit_bias={"808": -5, "28052": -5, "27": -5},
            stop_sequences=["\n"],
            model="ft:gpt-4o-mini-2024-07-18:paperplane-ai:plans-tree:AcZ8gHSo",
            presence_penalty=0,
            frequency_penalty=0.1,
        )
        return response.choices[0].message.content


async def main():
    api_factory = APIFactory(
        model="ft:gpt-4o-mini-2024-07-18:paperplane-ai:plans-tree:AcZ8gHSo"
    )
    sampler = ObjectiveTreeSampler(api_factory)
    objectives = await sampler.sample_tree(
        ["1. Set up a basic smelting operation", "2. Optimize furnace layout"], number=1
    )

    for objective in objectives:
        print(objective)


if __name__ == "__main__":
    asyncio.run(main())
