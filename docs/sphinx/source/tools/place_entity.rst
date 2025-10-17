place_entity
============

The ``place_entity`` tool allows you to place entities in the Factorio world at specific positions with optional direction and other parameters.

Function Signature
------------------

.. code-block:: python

   def place_entity(
       entity: Prototype,
       position: Position,
       direction: Direction = Direction.NORTH
   ) -> Entity

Parameters
----------

- ``entity``: A Prototype enum value representing the entity type to place
- ``position``: A Position object specifying where to place the entity
- ``direction``: A Direction enum value (optional, defaults to Direction.NORTH)

Returns
-------

Returns an Entity object representing the placed entity with its current state.

Usage Examples
--------------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   # Place a mining drill at the nearest iron ore patch
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=nearest(Resource.IronOre),
       direction=Direction.NORTH
   )
   print(f"Placed mining drill at {drill.position}")

Advanced Usage
^^^^^^^^^^^^^^

.. code-block:: python

   # Place multiple entities with specific positioning
   iron_pos = Position(x=10, y=5)
   
   # Place mining drill
   drill = place_entity(
       entity=Prototype.MiningDrill,
       position=iron_pos,
       direction=Direction.NORTH
   )
   
   # Place chest next to drill
   chest = place_entity(
       entity=Prototype.IronChest,
       position=Position(x=iron_pos.x, y=iron_pos.y + 2),
       direction=Direction.NORTH
   )
   
   print(f"Placed drill at {drill.position} and chest at {chest.position}")

Error Handling
--------------

The tool will raise exceptions in the following situations:

- Invalid entity type
- Invalid position (e.g., on water or overlapping existing entities)
- Insufficient resources for placement
- Invalid direction for the entity type

Example error handling:

.. code-block:: python

   try:
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=invalid_position,
           direction=Direction.NORTH
       )
   except ValueError as e:
       print(f"Failed to place entity: {e}")
       # Try alternative position
       valid_pos = nearest_buildable(Prototype.MiningDrill)
       drill = place_entity(
           entity=Prototype.MiningDrill,
           position=valid_pos,
           direction=Direction.NORTH
       )

Best Practices
--------------

1. **Check Position Validity**: Use ``nearest_buildable()`` to find valid positions
2. **Store Entity References**: Keep references to placed entities for later use
3. **Handle Errors Gracefully**: Use try-except blocks for robust error handling
4. **Consider Entity Dimensions**: Some entities require multiple tiles
5. **Validate Prerequisites**: Ensure required technology is researched

Common Pitfalls
---------------

1. **Overlapping Entities**: Placing entities on occupied tiles
2. **Invalid Directions**: Some entities have restricted direction options
3. **Resource Requirements**: Not having required items in inventory
4. **Technology Prerequisites**: Trying to place entities requiring unresearched technology
5. **Position Validation**: Not checking if position is buildable
