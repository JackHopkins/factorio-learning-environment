We downloaded 5000 Factorio blueprints from the public repository `factorio.school`.
We then filtered out blueprints that contain entities that are not supported by the environment, resulting in 1020 blueprints.
Each of these blueprints comprises a list entities, each with a position and orientation.



We group these into types, i.e "mining", "electricity", "logistics" etc.
We order the blueprints by the number of entities they contain, which gives the expected difficulty of the blueprint.

Our objective here is to:
1) convert each blueprint into a trajectory of actions that can be executed in the environment to build the blueprint.
2) perform dependency resolution to ensure that the player can gather the required items to build the blueprint.

Step 1 is done by a simple rule-based system that converts each entity into a sequence of actions.
Step 2 is done using an LLM with environmental feedback