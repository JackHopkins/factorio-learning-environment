classifier_prompt = """
Analyze if the following text contains specific Factorio game instructions or tutorials about actions that a player can take in the game.
Content about actions, commands, or steps related to building, mining, crafting, or automating = 'true'
Content about setting up the game, logging in, downloading, installing the game, or general information not related to gameplay mechanics = 'false'
Content about learning how to play the game, or generic advice such as 'Overcome unique challenges' = 'false'
Content containing mods or anything not in the base game = 'false'
Content referring to space, Gleba, Vulcanus, Factorio Space Age, Factorio V2.+ = 'false'

Respond with only 'true' or 'false'.
"""

extract_steps = """
Convert the Factorio guide into structured, nested, actionable steps that an AI program could execute. Format:
1. Main task
1.1. Sub task
1.1.1. Sub sub task 1
1.1.2. Sub sub task 2
1.2. Sub task 2 
...

Do NOT include any steps referencing the game interface, UI elements or setting up the game.
If any prior dependencies are mentioned, acquiring them should be included as an initial step.
Any steps that are general tips or not directly related to gameplay mechanics should be excluded.
Any steps relating to blueprints should be excluded.
Each step must be directly actionable in-game by an AI agent.
"""

finetune_system_prompt = """You are a helpful assistant that decides on the most appropriate Factorio game objective"""
