Tools Documentation
===================

This section contains detailed documentation for all available tools in the Factorio Learning Environment.

Tool Categories
---------------

**Inventory Management**
   Tools for managing inventories and items

**Entity Management**
   Tools for placing, removing, and managing entities

**Entity Queries**
   Tools for finding and inspecting entities

**Resource Management**
   Tools for resource collection and management

**Connection Management**
   Tools for creating connections between entities

**Crafting and Research**
   Tools for crafting items and managing research

**Movement and Control**
   Tools for player movement and game control

**Debugging and Output**
   Tools for debugging and output

Core Tools
----------

Inventory Management
~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/inspect_inventory
   tools/insert_item
   tools/extract_item

Entity Management
~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/place_entity
   tools/place_entity_next_to
   tools/pickup_entity
   tools/rotate_entity

Entity Queries
~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/get_entity
   tools/get_entities
   tools/nearest
   tools/nearest_buildable

Resource Management
~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/get_resource_patch
   tools/harvest_resource

Connection Management
~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/connect_entities
   tools/get_connection_amount

Crafting and Research
~~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/set_entity_recipe
   tools/get_prototype_recipe
   tools/craft_item
   tools/set_research
   tools/get_research_progress

Movement and Control
~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/move_to
   tools/sleep
   tools/launch_rocket

Debugging and Output
~~~~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 1

   tools/print

Tool Usage Patterns
-------------------

**Basic Usage**
   Most tools follow a simple pattern:

   .. code-block:: python

      # Get information
      result = tool_name(parameters)
      
      # Check result
      if result.get('success'):
           # Use the result
           data = result.get('data')
      else:
           # Handle error
           error = result.get('error')

**Error Handling**
   All tools return structured results with error information:

   .. code-block:: python

      result = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(10, 20),
          direction=Direction.NORTH
      )
      
      if result.get('success'):
           entity = result.get('entity')
           print(f"Placed entity: {entity}")
      else:
           error = result.get('error')
           print(f"Error: {error}")

**Chaining Operations**
   Tools can be chained together for complex operations:

   .. code-block:: python

      # Place a mining drill
      drill = place_entity(
          entity=Prototype.MiningDrill,
          position=nearest(Resource.IronOre),
          direction=Direction.NORTH
      )
      
      # Place a chest next to it
      chest = place_entity_next_to(
          entity=Prototype.IronChest,
          reference_position=drill.drop_position,
          direction=Direction.SOUTH
      )
      
      # Connect them
      connect_entities(drill, chest)

Best Practices
--------------

1. **Check Results**: Always check tool return values
2. **Handle Errors**: Implement proper error handling
3. **Use Type Hints**: Leverage type information for better code
4. **Chain Operations**: Combine tools for complex tasks
5. **Monitor Performance**: Track tool usage and performance
6. **Document Usage**: Document tool usage patterns
7. **Test Thoroughly**: Test all tool combinations

Tool Development
----------------

**Creating Custom Tools**
   See the :doc:`customization guide <../customization/tools>` for information on creating custom tools.

**Tool Testing**
   Test tools thoroughly with various scenarios:

   - Valid inputs
   - Invalid inputs
   - Edge cases
   - Error conditions
   - Performance scenarios

**Tool Documentation**
   Document tools with:

   - Clear descriptions
   - Parameter specifications
   - Return value documentation
   - Usage examples
   - Best practices
   - Failure modes
