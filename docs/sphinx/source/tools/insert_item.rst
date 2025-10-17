insert_item
===========

Places items from player inventory into entities.

Overview
--------

The `insert_item` tool allows agents to transfer items from their inventory into entity inventories such as chests, furnaces, and other storage containers.

Parameters
----------

**entity** (Entity)
   The entity to insert items into.

**item** (str)
   The name of the item to insert.

**count** (int, optional)
   The number of items to insert. Defaults to 1.

Returns
-------

Dictionary containing:

- **success** (bool): Whether the insertion succeeded
- **inserted_count** (int): Number of items actually inserted
- **entity** (Entity): The updated entity
- **error** (str): Error message (if failed)

Examples
--------

**Basic Usage**
   .. code-block:: python

      # Insert iron ore into a chest
      result = insert_item(
          entity=chest,
          item='iron-ore',
          count=10
      )
      
      if result.get('success'):
           print(f"Inserted {result.get('inserted_count')} iron ore")
      else:
           print(f"Error: {result.get('error')}")

**Insert Multiple Items**
   .. code-block:: python

      # Insert different items into a furnace
      items_to_insert = [
           {'item': 'iron-ore', 'count': 50},
           {'item': 'coal', 'count': 10}
      ]
      
      for item_data in items_to_insert:
           result = insert_item(
               entity=furnace,
               item=item_data['item'],
               count=item_data['count']
           )
           
           if result.get('success'):
                print(f"Inserted {result.get('inserted_count')} {item_data['item']}")

Best Practices
--------------

1. **Check Entity Type**: Ensure the entity supports item insertion
2. **Verify Item Compatibility**: Check that the item can be inserted into the entity
3. **Handle Partial Insertions**: Account for cases where not all items can be inserted
4. **Monitor Inventory**: Track inventory changes after insertion

Failure Modes
-------------

**Invalid Entity**
   - **Error**: "Entity does not support item insertion"
   - **Cause**: Entity type doesn't support inventory
   - **Solution**: Check entity type before insertion

**Item Not Available**
   - **Error**: "Item not available in player inventory"
   - **Cause**: Player doesn't have the required item
   - **Solution**: Check player inventory before insertion

**Entity Full**
   - **Error**: "Entity inventory is full"
   - **Cause**: Entity cannot accept more items
   - **Solution**: Check entity capacity or use different entity

Related Tools
-------------

- :doc:`inspect_inventory` - Check inventory contents
- :doc:`extract_item` - Remove items from entities
- :doc:`get_entities` - Find entities with storage
