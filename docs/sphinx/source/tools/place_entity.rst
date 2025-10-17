place_entity
============

Places entities in the world at specified positions.

Overview
--------

The `place_entity` tool allows agents to place various entities in the game world. It handles placement validation, direction setting, and returns information about the placed entity.

Parameters
----------

**entity** (Prototype)
   The type of entity to place. Must be a valid Prototype enum value.

**position** (Position)
   The position where to place the entity. Must be a valid Position object.

**direction** (Direction, optional)
   The direction to orient the entity. Defaults to Direction.NORTH.

Returns
-------

Dictionary containing:

- **success** (bool): Whether the placement succeeded
- **entity** (Entity): The placed entity object (if successful)
- **error** (str): Error message (if failed)

Examples
--------

**Basic Usage**
   .. code-block:: python

      # Place a mining drill
      result = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(10, 20),
          direction=Direction.NORTH
      )
      
      if result.get('success'):
           drill = result.get('entity')
           print(f"Placed mining drill at {drill.position}")
      else:
           print(f"Error: {result.get('error')}")

**With Resource Location**
   .. code-block:: python

      # Find iron ore and place mining drill
      iron_pos = nearest(Resource.IronOre)
      if iron_pos:
           result = place_entity(
               entity=Prototype.MiningDrill,
               position=iron_pos,
               direction=Direction.NORTH
           )
           
           if result.get('success'):
                drill = result.get('entity')
                print(f"Placed mining drill on iron ore at {drill.position}")

**Direction Examples**
   .. code-block:: python

      # Place entities in different directions
      drill_north = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(0, 0),
          direction=Direction.NORTH
      )
      
      drill_south = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(10, 0),
          direction=Direction.SOUTH
      )
      
      drill_east = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(20, 0),
          direction=Direction.EAST
      )
      
      drill_west = place_entity(
          entity=Prototype.MiningDrill,
          position=Position(30, 0),
          direction=Direction.WEST
      )

Best Practices
--------------

1. **Check Position Validity**: Ensure the position is valid for the entity type
2. **Handle Errors**: Always check the success flag and handle errors
3. **Use Appropriate Directions**: Choose directions that make sense for the entity
4. **Validate Resources**: Ensure required resources are available
5. **Monitor Placement**: Check that entities are placed correctly

Failure Modes
-------------

**Invalid Entity Type**
   - **Error**: "Invalid entity type 'invalid'. Expected Prototype enum value."
   - **Cause**: Using an invalid entity type
   - **Solution**: Use valid Prototype enum values

**Invalid Position**
   - **Error**: "Position (x, y) is not valid for entity type"
   - **Cause**: Position conflicts with existing entities or terrain
   - **Solution**: Choose a different position or clear the area

**Insufficient Resources**
   - **Error**: "Insufficient resources to place entity"
   - **Cause**: Not enough items in inventory
   - **Solution**: Ensure required items are available

**Invalid Direction**
   - **Error**: "Invalid direction for entity type"
   - **Cause**: Direction not supported by entity type
   - **Solution**: Use supported directions for the entity

Related Tools
-------------

- :doc:`place_entity_next_to` - Place entities relative to others
- :doc:`pickup_entity` - Remove entities from the world
- :doc:`rotate_entity` - Change entity orientation
- :doc:`nearest` - Find nearest resources or entities
- :doc:`nearest_buildable` - Find valid building locations
