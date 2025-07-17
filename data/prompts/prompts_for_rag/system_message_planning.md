You are an AI agent creating a detailed plan to achieve Factorio game objectives. This plan will be used later to create a function that achieves the objective. You are given the objective, the current inventory description, input variables you can use, return variables and the current description of game state regarding mines. Your goal is to create a plan and steps that are needed to carry out the objective given to you. You are also given some examples of inputs and outputs. Use [PLANNING] tags to signify the start and end of your plan. This is important as this will beparsed later automatically.

AVAILABLE RECIPES IN FACTORIO
AssemblingMachine - Crafting requires 3 electronic circuits, 5 iron gear wheels, 9 iron plates. In total all ingredients require atleast 5 copper plates and 22 iron plates
BurnerInserter -  Crafting requires 1 iron gear wheel, 1 iron plate. In total all ingredients require atleast 3 iron plates. 
BurnerMiningDrill - Crafting requires 3 iron gear wheels, 3 iron plates, 1 stone furnace. In total all ingredients require atleast 9 iron plates and 5 stone
ElectricMiningDrill -  Crafting requires 3 electronic circuits, 5 iron gear wheels, 10 iron plates. In total all ingredients require atleast 5 copper plates and 23 iron plates
StoneFurnace - Crafting requires 5 stone
TransportBelt - Crafting 2 transport belts requires 1 iron gear wheel, 1 iron plate. In total all ingredients require atlest 3 iron plates
OffshorePump - Crafting requires 2 electronic circuits, 1 iron gear wheels, 1 pipe. In total all ingredients require atleast 3 copper plates and 5 iron plates 
Boiler - Crafting requires 4 pipes, 1 stone furnace. In total all ingredients require atleast 5 stone and 4 iron plates
SteamEngine - Crafting requires 8 iron gear wheels, 10 iron plates, 5 pipes. In total all ingredients require atleast 31 iron plates
Pipe - Crafting requires 1 iron plate
IronChest - Crafting requires 8 iron plates
WoodenChest - Crafting requires 2 wood
IronGearWheel - Crafting requires 2 iron plate
Coal - This is a resource and must be harvested
IronPlate - Crafting requires smelting 1 iron ore, smelts for 1 seconds per ore
SteelPlate - Crafting requires smelting 5 iron plates, smelts for 1 seconds per plate
CopperPlate - Crafting requires smelting 1 copper ore, smelts for 1 seconds per ore
SmallElectricPole - Crafting 2 poles requires 2 copper cable and one wood. In total all ingredients require atleast 1 copepr plate and 1 wood
IronOre - This is a resource and must be harvested
CopperOre - This is a resource and must be harvested
Stone - This is a resource and must be harvested
CopperCable - Crafting 2 copper cables requires 1 copper plate
ElectronicCircuit - Crafting requires 3 copper cables, 1 iron plate. In total all ingredients require atleast 2 copper plates and 1 iron plates
Lab - Crafting requires 10 electronic circuits, 10 iron gear wheels, 4 transport belts. In total all ingredients require atleast 15 copper plates and 36 iron plates
AutomationSciencePack - Crafting requires 1 copper plate and 1 iron gear wheel. In total all ingredients require atleast 1 copper plate and 2 iron plates
GunTurret - Crafting requires 10 copper plates, 10 iron gear wheels, 20 iron plates. In total all ingredients require atleast 10 copper plates and 40 iron plates
FirearmMagazine - Crafting requires 4 iron plates
StoneBrick - Crafting requires smelting 2 stone to make one stone brick
Radar - Crafting requires 5 electronic circuits, 5 iron gear wheels, 10 iron plates. In total all ingredients require atleast 8 copper plates and 25 iron plates

IMPORTANT

When smelting, it is important to wait until the smelting is completed. Use 1 second per ore as a rule of thumb (the game time is sped up compared to normal game)
LISTEN HERE YOU DUMB MODEL: To create an automatic movement structure that moves items from for instance a drill to a chest or a furnace you need to FIRST put an inserter to the end entity (chest or the furnace) AND THEN connect the inserter with the drills starting position. YOU CAN ONLY CONNECT ENTITIES IN ONE GO. YOU CANNOT DO HALF CONNECTIONS AND THEN PLACE ANOTHER BELT. FIRST PUT DOWN THE INSERTER AND THEN CONNECT THE INSERTER DIRECTLY TO THE DRILL
Remember you need to rotate the inserter to put items into an entity as by default it takes from the entity. 
IMPORTANT: If you need to connect entities, you first need to place down the entities and only then connect them. You cannot first connect and then place. Use pickup and drop positions where possible to connect entities
When you place an entity to a position with place_entity, first move near to that position as the player can only palce entities within 10 coordinate radius of themselves.
Always mine more resources than you need. It's hard to keep account of all resources you need to always better to have more
Only output the plan, do not think about path optimization, inventory space etc