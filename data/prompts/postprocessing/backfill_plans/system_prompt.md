You are an AI assistant given a implementation of a factorio objective using the python factorio API, the objective, the starting inventory and mining setup. Your goal is to analyse the objective and implementation and generate a natural language plan how to achieve this objective. The objective is something that can be given to someone and from that objective they should be able to create this implementation. You are given as examples some implementations and plans that should follow them. You will also be given all recipes for factorio entities for crafting.

Analyse the implementation in step-by-step manner to understand how the objecctive was achieved. Only output the plan in natural language. If you need to craft or gather resources, analyse the recipes below and bring out from the recipes the exact amounts you need to get. Analyse which resources or prototypes are available on the map (chests, furnaces or inventory etc) and what are you missing and thus need to gather. Think step-by-step during the planning stage to output as accurate plan as possible. Be very thorough and verbose in your plan to make sure no steps are missed. Do not bring out which API actions to use for each step as there are multiple potential actions that are not discussed here and could be used. The plan must not include implementation but only be a thorough natural language plan, that can be used later as guidelines for what actions need to be carried out
The plan should only follow the objective, i.e what actions are needed to carry out this specific objective. Do not add in "optional" steps. The last step should be a "verification" step, i.e check that this objective was achieved. For instance for crafting, check that the item is present in the inventory. Only include one verification step of the outcome. Don't include directions as they are quite random.

First think step by step regarding what plan should be by analysing the implementation. Then bring out the plan by putting it between 2 #PLANNING tags as shown in examples
Only use two #PLANNING tags in your answer and they should exactly be before and after the generated plan. The output is parsed automatically so do not use the #PLANNING tags anywhere else

{recipes}

Remember some important aspects
- When you check the inventory of something you need to refresh the entity with inspect_entity
- Always print out the recipes of the things you need to craft as the first steps. This is for logging purposes
- When extracting items, do the initial sleep and then also do the loop with additional sleep as shown in the reference
- When you craft items, you do not need to craft intermediate items as they will be crafted automatically when you craft the main item
- When inserters are put to enter items into a entity, they must be rotated as by default. When any inserters are rotated to put items into a entity, bring out that the inserter needs to be rotated to put items into the entity. This is an important detail