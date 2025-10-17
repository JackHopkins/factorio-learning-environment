inspect_inventory
=================

The ``inspect_inventory`` tool allows you to check the contents of player or entity inventories, providing detailed information about stored items and their quantities.

Function Signature
------------------

.. code-block:: python

   def inspect_inventory(entity: Optional[Entity] = None) -> Inventory

Parameters
----------

- ``entity``: Optional Entity object to inspect. If None, inspects the player's inventory.

Returns
-------

Returns an Inventory object containing:
- Item names as keys
- Item quantities as values
- Additional inventory metadata

Usage Examples
--------------

Player Inventory
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Check player inventory
   inventory = inspect_inventory()
   print(f"Player inventory: {inventory}")
   
   # Check specific items
   if inventory['iron-ore'] > 100:
       print("Have enough iron ore")
   else:
       print("Need more iron ore")

Entity Inventory
^^^^^^^^^^^^^^^^

.. code-block:: python

   # Check chest inventory
   chest = get_entity(Position(x=10, y=5))
   if chest:
       chest_inventory = inspect_inventory(chest)
       print(f"Chest contains: {chest_inventory}")
       
       # Check if chest has space
       if chest_inventory.total_space < chest_inventory.max_space:
           print("Chest has space for more items")

Advanced Usage
^^^^^^^^^^^^^^

.. code-block:: python

   # Check multiple entity inventories
   entities = get_entities()
   for entity in entities:
       if entity.name in ['iron-chest', 'steel-chest']:
           inventory = inspect_inventory(entity)
           print(f"{entity.name} at {entity.position}: {inventory}")
           
           # Check for specific items
           if 'iron-plate' in inventory:
               print(f"Found {inventory['iron-plate']} iron plates")

Inventory Methods
-----------------

The returned Inventory object provides several useful methods:

.. code-block:: python

   inventory = inspect_inventory()

   # Check if item exists
   if inventory.has_item('iron-ore'):
       print("Has iron ore")

   # Get item count
   iron_count = inventory.get_count('iron-ore')
   print(f"Iron ore count: {iron_count}")

   # Get total items
   total_items = inventory.total_items()
   print(f"Total items: {total_items}")

   # Check inventory space
   available_space = inventory.available_space()
   print(f"Available space: {available_space}")

Error Handling
--------------

The tool will raise exceptions in the following situations:

- Entity not found or invalid
- Entity has no inventory
- Network communication errors

Example error handling:

.. code-block:: python

   try:
       inventory = inspect_inventory(invalid_entity)
   except ValueError as e:
       print(f"Failed to inspect inventory: {e}")
   except Exception as e:
       print(f"Unexpected error: {e}")

Best Practices
--------------

1. **Check Entity Validity**: Verify entity exists before inspecting
2. **Handle Empty Inventories**: Check for empty or None results
3. **Use Inventory Methods**: Use provided methods for better functionality
4. **Cache Results**: Store inventory data for multiple operations
5. **Validate Items**: Check if specific items exist before accessing

Common Pitfalls
---------------

1. **None Entity**: Passing None when expecting an entity
2. **Invalid Entity**: Inspecting non-inventory entities
3. **Key Errors**: Accessing non-existent items directly
4. **Stale Data**: Using outdated inventory information
5. **Performance**: Inspecting inventories too frequently
