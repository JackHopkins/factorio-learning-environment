Creating Custom Tools
=====================

This guide explains how to create custom tools for FLE to extend agent capabilities with specialized functionality.

Overview
--------

A custom tool requires three components:

1. **agent.md**: Documentation for the agent
2. **client.py**: Python interface
3. **server.lua**: Lua implementation

Tool Structure
--------------

Tools live in ``fle/env/tools/``:

.. code-block:: text

   fle/env/tools/
   ├── admin/          # Non-agent accessible tools
   └── agent/          # Agent-accessible tools
       └── my_tool/    # Your custom tool
           ├── agent.md
           ├── client.py
           └── server.lua

Step-by-Step Guide
------------------

Step 1: Create Tool Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new directory in ``fle/env/tools/agent/``:

.. code-block:: bash

   mkdir fle/env/tools/agent/my_tool

Step 2: Create client.py
~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``client.py`` with a class inheriting from ``Tool``:

.. code-block:: python

   from typing import Optional
   from fle.env.tools.tool import Tool
   from fle.env.entities import Entity
   from fle.env.models import Position

   class MyTool(Tool):
       """
       Brief description of what your tool does.
       """

       def __call__(self,
                    entity: Entity,
                    target_position: Position,
                    quantity: Optional[int] = None) -> dict:
           """
           Detailed description of the tool's functionality.

           Args:
               entity: The entity to operate on
               target_position: Where to perform the action
               quantity: Optional quantity parameter

           Returns:
               Dictionary containing result information

           Raises:
               InvalidParameterException: If parameters are invalid
               EntityNotFoundException: If entity doesn't exist
           """
           # Call server-side implementation
           result = self.execute(
               entity=entity.name,
               position=target_position.to_dict(),
               quantity=quantity
           )

           return result

**Key Requirements:**

- Inherit from ``Tool``
- Implement ``__call__`` method
- Use type annotations
- Call ``self.execute()`` to invoke server-side logic
- Document parameters, return values, and exceptions

Step 3: Create server.lua
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``server.lua`` with the game logic:

.. code-block:: lua

   -- Register the tool action
   global.actions.my_tool = function(params)
       -- Extract parameters
       local entity_name = params.entity
       local position = params.position
       local quantity = params.quantity or 1

       -- Validate parameters
       if not entity_name or not position then
           return {
               success = false,
               error = "Missing required parameters"
           }
       end

       -- Find the entity
       local entity = game.surfaces[1].find_entity(entity_name, position)
       if not entity then
           return {
               success = false,
               error = "Entity not found at position"
           }
       end

       -- Perform the action using Factorio API
       local result = entity.some_action(quantity)

       -- Return serialized result
       return {
           success = true,
           entity = serialize_entity(entity),
           result = result
       }
   end

**Key Requirements:**

- Register function in ``global.actions``
- Validate all parameters
- Use `Factorio API <https://lua-api.factorio.com/1.1.110/>`_
- Return a serializable table
- Include error handling

Step 4: Create agent.md
~~~~~~~~~~~~~~~~~~~~~~~~

Create ``agent.md`` with agent-facing documentation:

.. code-block:: markdown

   # My Tool

   ## Description

   Brief description of what the tool does and when to use it.

   ## Usage

   ```python
   result = my_tool(
       entity=my_entity,
       target_position=Position(x=10, y=20),
       quantity=5
   )
   ```

   ## Parameters

   - `entity` (Entity): The entity to operate on
   - `target_position` (Position): Where to perform the action
   - `quantity` (int, optional): How many items to process. Defaults to 1.

   ## Returns

   Dictionary containing:
   - `success` (bool): Whether the operation succeeded
   - `entity` (Entity): Updated entity object
   - `result`: Operation-specific result data

   ## Best Practices

   1. Always check entity status before calling
   2. Use reasonable quantity values
   3. Verify results with assertions

   ## Common Pitfalls

   - Entity must exist at the specified position
   - Target position must be valid
   - Quantity cannot exceed inventory limits

   ## Examples

   ### Basic Usage

   ```python
   entity = get_entity(Prototype.Chest, Position(x=0, y=0))
   result = my_tool(entity, Position(x=5, y=5), quantity=10)
   assert result['success']
   ```

   ### Error Handling

   ```python
   try:
       result = my_tool(entity, position)
   except InvalidParameterException as e:
       print(f"Invalid parameters: {e}")
   ```

Step 5: Test Your Tool
~~~~~~~~~~~~~~~~~~~~~~~

Create a test in ``fle/env/tests/actions/``:

.. code-block:: python

   import pytest
   from fle.env.gym_env import FactorioGymEnv
   from fle.env.models import Position

   def test_my_tool():
       env = FactorioGymEnv()
       obs = env.reset()

       # Setup test scenario
       code = """
   entity = place_entity(
       Prototype.Chest,
       Position(x=0, y=0),
       Direction.NORTH
   )

   # Test your tool
   result = my_tool(
       entity=entity,
       target_position=Position(x=5, y=5),
       quantity=10
   )

   print(result)
   assert result['success']
   """

       action = Action(agent_idx=0, code=code)
       obs, reward, done, truncated, info = env.step(action)

       # Verify results
       assert "success" in obs['raw_text']
       env.close()

Complete Example
----------------

Here's a complete example of a tool that transfers items between two chests:

**client.py:**

.. code-block:: python

   from typing import Optional
   from fle.env.tools.tool import Tool
   from fle.env.entities import Entity

   class TransferItems(Tool):
       """Transfers items between two entities."""

       def __call__(self,
                    source: Entity,
                    destination: Entity,
                    item: str,
                    quantity: int) -> dict:
           """
           Transfer items from source to destination.

           Args:
               source: Entity to take items from
               destination: Entity to place items into
               item: Item prototype name
               quantity: Number of items to transfer

           Returns:
               Dictionary with transfer results

           Raises:
               InsufficientItemsException: Not enough items in source
               InventoryFullException: Destination inventory is full
           """
           result = self.execute(
               source=source.name,
               source_position=source.position.to_dict(),
               destination=destination.name,
               destination_position=destination.position.to_dict(),
               item=item,
               quantity=quantity
           )

           return result

**server.lua:**

.. code-block:: lua

   global.actions.transfer_items = function(params)
       local source = game.surfaces[1].find_entity(
           params.source,
           params.source_position
       )
       local destination = game.surfaces[1].find_entity(
           params.destination,
           params.destination_position
       )

       if not source or not destination then
           return {success = false, error = "Entity not found"}
       end

       -- Get source inventory
       local source_inv = source.get_inventory(defines.inventory.chest)
       if not source_inv then
           return {success = false, error = "No source inventory"}
       end

       -- Check if enough items
       local available = source_inv.get_item_count(params.item)
       if available < params.quantity then
           return {
               success = false,
               error = "Insufficient items",
               available = available
           }
       end

       -- Transfer items
       local removed = source_inv.remove({
           name = params.item,
           count = params.quantity
       })

       local dest_inv = destination.get_inventory(defines.inventory.chest)
       local inserted = dest_inv.insert({
           name = params.item,
           count = removed
       })

       -- Return any excess
       if inserted < removed then
           source_inv.insert({
               name = params.item,
               count = removed - inserted
           })
       end

       return {
           success = true,
           transferred = inserted,
           source = serialize_entity(source),
           destination = serialize_entity(destination)
       }
   end

**agent.md:**

.. code-block:: markdown

   # Transfer Items

   Transfer items between two entities' inventories.

   ## Usage

   ```python
   source_chest = get_entity(Prototype.IronChest, Position(x=0, y=0))
   dest_chest = get_entity(Prototype.IronChest, Position(x=5, y=5))

   result = transfer_items(
       source=source_chest,
       destination=dest_chest,
       item='iron-plate',
       quantity=50
   )
   ```

   ## Best Practices

   1. Check source has enough items before transferring
   2. Verify destination has space
   3. Handle partial transfers gracefully

Automatic Registration
----------------------

Once your tool is created, it will be automatically:

1. Discovered by the environment
2. Available to agents in the Python namespace
3. Documented in agent context with the ``agent.md`` content

No additional registration steps are needed!

Tips & Best Practices
----------------------

1. **Keep It Simple**: Tools should do one thing well
2. **Validate Early**: Check parameters in both client and server
3. **Document Thoroughly**: Agents rely on good documentation
4. **Handle Errors**: Provide clear error messages
5. **Test Extensively**: Create comprehensive test cases
6. **Use Type Hints**: Make the interface clear with Python type annotations
7. **Serialize Carefully**: Ensure all return values are JSON-serializable

Common Patterns
---------------

Querying Entity State
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: lua

   local entity = game.surfaces[1].find_entity(name, position)
   return serialize_entity(entity)

Modifying Inventory
~~~~~~~~~~~~~~~~~~~

.. code-block:: lua

   local inventory = entity.get_inventory(defines.inventory.chest)
   inventory.insert({name = item, count = quantity})

Moving Entities
~~~~~~~~~~~~~~~

.. code-block:: lua

   local success = entity.teleport(new_position)

Checking Validity
~~~~~~~~~~~~~~~~~

.. code-block:: lua

   if not entity.valid then
       return {success = false, error = "Entity no longer exists"}
   end

Next Steps
----------

- Review :doc:`core_tools` for implementation patterns
- See :doc:`overview` for architecture details
- Check the `Factorio Lua API <https://lua-api.factorio.com/1.1.110/>`_
- Join the `Discord <https://discord.gg/zKaV2skewa>`_ for help
