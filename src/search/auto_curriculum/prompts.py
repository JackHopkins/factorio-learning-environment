# prompts.py
TASK_SYSTEM_PROMPT= """You are an AI generating increasingly complex tasks for a Factorio automation agent.
Given the production targets and history of previous tasks, generate a new task description.
The task should be more sophisticated than previous tasks when possible, while being achievable
with the target production quantities."""

RECENT_TASK_HISTORY_PROMPT = \
"""
Previous Task: {previous_task}
Production/Loss achieved:
Input (consumed):
{input}
Output (produced):
{output}
---
"""

TASK_GENERATION_PROMPT = """
{recent_task_history}

Target production quantities for new task:
Input (resources to consume):
{input_resources}
Output (items to produce):
{output_resources}

Based on these targets and previous tasks, create a single concise task description that:
1. Focuses on automation and factory building
2. Builds upon previous accomplishments when possible
3. Introduces new production concepts if appropriate
4. Is achievable with the target quantities
5. Describes what to build/create, not the specific steps
6. Be specific and quantitative regarding the end goal

Task description:"""

USER_TASK_PROMPT = """Your starting inventory is `{inventory}`. Your initial mining setup is: `{mining_setup}`.
Create a python script that achieves the following task:
{task_description}

The task should aim to produce these approximate item quantities:
{target_quantities}"""