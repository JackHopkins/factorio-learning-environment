import asyncio
from typing import Dict, List

from fle.agents.llm.api_factory import APIFactory


class PlanGenerator:
    def __init__(self, api_factory: "APIFactory"):
        self.llm = api_factory

    def _get_example_prompt(self) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": "You generate Factorio automation plans. Follow the format in the examples.",
            },
            {"role": "user", "content": "Generate a plan"},
            {
                "role": "assistant",
                "content": '''"""
Objective: Craft 2 burner inserters
The final success should be checked by looking if the burner inserters are in inventory
"""

"""
Planning:
1) Print recipes for the entities we need to craft
2) Gather resources (iron plates, stone) for crafting
3) Craft a burner mining drill  
4) Place the burner mining drill on an iron ore patch
5) Place the stone furnace below the burner mining drill
6) Connect the burner mining drill to the stone furnace using a burner inserter
7) Fuel both the burner mining drill and stone furnace with coal
8) Verify the setup by checking if iron plates are being produced
"""''',
            },
            {"role": "user", "content": "Another plan"},
            {
                "role": "assistant",
                "content": '''"""
Objective: Craft and place a lab at the origin

Planning:
1) Print recipe for Lab
2) Print recipes for intermediate products (iron gear wheels, transport belts, electronic circuits)  
3) Print recipe for Assembling Machine 1 (optional)
4) Use existing Burner Mining Drill and Stone Furnace to produce iron plates for crafting
5) Craft intermediate products: iron gear wheels, transport belts, electronic circuits
6) Craft the Lab
7) Move to origin and place the Lab
"""''',
            },
            {"role": "user", "content": "Generate a plan for making transport belts"},
            {
                "role": "assistant",
                "content": '''"""
Objective: We need to craft 4 transport belts
Planning: We need to print out the recipe for transport belts and then craft them. We have the required resources in our inventory so we can directly craft the transport belts
"""''',
            },
        ]

    async def generate_plan(self) -> str:
        messages = self._get_example_prompt()
        messages.append({"role": "user", "content": "Generate another automation plan"})

        response = self.llm.call(messages=messages, temperature=0.7, max_tokens=1024)

        return response.choices[0].message.content

    async def generate_plans(self, n: int) -> List[str]:
        plans = []
        for _ in range(n):
            plan = await self.generate_plan()
            print(plan)
            plans.append(plan)
        return plans


if __name__ == "__main__":
    llm = APIFactory(
        "ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91"
    )
    plan_generator = PlanGenerator(api_factory=llm)
    asyncio.run(plan_generator.generate_plans(n=3))
