## TIPS FOR QUERYING INFORMATION
- Make sure to query information using the query_information tool
- Use the tool like you would research different areas on the wiki
- The pages have info regarding how to use the api, how to carry out different actions and general factorio knowledge

## TIPS WHEN CREATING STRUCTURES
- When a entity has status "WAITING_FOR_SPACE_IN_DESTINATION", it means the there is no space in the drop position. For instance, a mining drill will have status WAITING_FOR_SPACE_IN_DESTINATION when the entities it mines are not being properly collected by a furnace or a chest or transported away from drop position with transport belts
- Make sure to always put 20+ fuel into all entities that require fuel. It's easy to mine more coal, so it's better to insert in abundance 
- Keep it simple! Only use transport belts if you need them. Use chests and furnaces to catch the ore directly from drills
- Inserters put items into entities or take items away from entities. You need to add inserters when items need to be automatically put into entities like chests, assembling machines, furnaces, boilers etc. The only exception is you can put a chest directly at drills drop position, that catches the ore directly or a furnace with place_entity_next_to(drill.drop_position), where the furnace will be fed the ore
- have at least 10 spaces between different factory sections