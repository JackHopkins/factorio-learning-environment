extract_item
============

Removes items from entity inventories.

Overview
--------

The `extract_item` tool allows agents to remove items from entity inventories and transfer them to the player's inventory.

Parameters
----------

**entity** (Entity)
   The entity to extract items from.

**item** (str)
   The name of the item to extract.

**count** (int, optional)
   The number of items to extract. Defaults to 1.

Returns
-------

Dictionary containing:

- **success** (bool): Whether the extraction succeeded
- **extracted_count** (int): Number of items actually extracted
- **entity** (Entity): The updated entity
- **error** (str): Error message (if failed)

Examples
--------

**Basic Usage**
   .. code-block:: python

      # Extract iron ore from a chest
      result = extract_item(
          entity=chest,
          item='iron-ore',
          count=10
      )
      
      if result.get('success'):
           print(f"Extracted {result.get('extracted_count')} iron ore")
      else:
           print(f"Error: {result.get('error')}")

**Extract All Items**
   .. code-block:: python

      # Extract all items from an entity
      inventory = inspect_inventory(entity=chest)
      for item, count in inventory.items():
           if count > 0:
                result = extract_item(
                    entity=chest,
                    item=item,
                    count=count
                )
                
                if result.get('success'):
                     print(f"Extracted {result.get('extracted_count')} {item}")

Best Practices
--------------

1. **Check Entity Contents**: Verify the entity has the items to extract
2. **Handle Partial Extractions**: Account for cases where not all items can be extracted
3. **Monitor Player Inventory**: Track player inventory changes
4. **Use Appropriate Counts**: Don't extract more items than available

Failure Modes
-------------

**Invalid Entity**
   - **Error**: "Entity does not support item extraction"
   - **Cause**: Entity type doesn't support inventory
   - **Solution**: Check entity type before extraction

**Item Not Available**
   - **Error**: "Item not available in entity inventory"
   - **Cause**: Entity doesn't have the required item
   - **Solution**: Check entity inventory before extraction

**Player Inventory Full**
   - **Error**: "Player inventory is full"
   - **Cause**: Player cannot accept more items
   - **Solution**: Clear player inventory or use storage

Related Tools
-------------

- :doc:`inspect_inventory` - Check inventory contents
- :doc:`insert_item` - Add items to entities
- :doc:`get_entities` - Find entities with storage
