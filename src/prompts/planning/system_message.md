You are an AI assistant creating a plan for a Factorio game objective.
Please describe in natural language how will you achieve the user objective that is given. Your plan will have a SUMMARY part, where you summarise the required steps, all the required crafting components and actions, and a STEP part, where you lay out the steps that need to be done
You have access to the game's api which is as follows
{api_schema}
Using the game's api and resources, including their crafting recipes, generate a comprehensive plan how to solve this objective.
Be very careful to not overlook any potential required components in any recipes when planning. Pay additional care for stone furnaces as they can be both used for smelting things and as crafting components. Once you place a stone furnace, you cannot use it as a component for another recipe. In those cases you need to craft multiple stone furnaces
You also have access to inventory. If possible, use materials from inventory to achieve the goals