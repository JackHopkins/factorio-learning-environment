inspect_inventory
=================

Checks contents of player or entity inventories.

Overview
--------

The `inspect_inventory` tool allows agents to examine the contents of inventories. It supports various inventory types including player inventories, chests, furnaces, and other entities with storage capabilities.

Parameters
----------

**entity** (Entity, optional)
   The entity whose inventory to inspect. If not provided, inspects the player's inventory.

**inventory_type** (str, optional)
   The type of inventory to inspect. Options: 'player', 'entity', 'all'.

Returns
-------

Dictionary containing:

- **success** (bool): Whether the inspection succeeded
- **inventory** (Inventory): The inventory contents
- **entity** (Entity): The entity whose inventory was inspected (if applicable)
- **error** (str): Error message (if failed)

Examples
--------

**Basic Usage**
   .. code-block:: python

      # Inspect player inventory
      result = inspect_inventory()
      
      if result.get('success'):
           inventory = result.get('inventory')
           print(f"Player inventory: {inventory}")
           
           # Check specific items
           iron_ore = inventory.get('iron-ore', 0)
           coal = inventory.get('coal', 0)
           print(f"Iron ore: {iron_ore}, Coal: {coal}")
      else:
           print(f"Error: {result.get('error')}")

**Entity Inventory**
   .. code-block:: python

      # Inspect entity inventory
      entities = get_entities()
      for entity in entities:
           if entity.name == 'iron-chest':
                result = inspect_inventory(entity=entity)
                
                if result.get('success'):
                     inventory = result.get('inventory')
                     print(f"Chest inventory: {inventory}")
                     
                     # Check if chest is full
                     total_items = sum(inventory.values())
                     if total_items > 0:
                          print(f"Chest contains {total_items} items")
                break

**Inventory Analysis**
   .. code-block:: python

      # Analyze inventory contents
      result = inspect_inventory()
      
      if result.get('success'):
           inventory = result.get('inventory')
           
           # Count total items
           total_items = sum(inventory.values())
           print(f"Total items: {total_items}")
           
           # List all items
           for item, count in inventory.items():
                if count > 0:
                     print(f"  {item}: {count}")
           
           # Check for specific resources
           resources = ['iron-ore', 'copper-ore', 'coal', 'stone']
           for resource in resources:
                count = inventory.get(resource, 0)
                if count > 0:
                     print(f"Have {count} {resource}")

**Inventory Filtering**
   .. code-block:: python

      # Check for specific items
      result = inspect_inventory()
      
      if result.get('success'):
           inventory = result.get('inventory')
           
           # Check for mining equipment
           mining_items = ['mining-drill', 'burner-mining-drill']
           for item in mining_items:
                count = inventory.get(item, 0)
                if count > 0:
                     print(f"Have {count} {item}")
           
           # Check for building materials
           building_materials = ['iron-plate', 'copper-plate', 'stone']
           total_materials = sum(inventory.get(item, 0) for item in building_materials)
           print(f"Total building materials: {total_materials}")

Best Practices
--------------

1. **Check Success**: Always verify the inspection succeeded
2. **Handle Empty Inventories**: Account for empty inventories
3. **Use Inventory Methods**: Leverage inventory utility methods
4. **Monitor Changes**: Track inventory changes over time
5. **Error Handling**: Implement proper error handling

Failure Modes
-------------

**Invalid Entity**
   - **Error**: "Entity does not have an inventory"
   - **Cause**: Entity type doesn't support inventory
   - **Solution**: Check entity type before inspection

**Entity Not Found**
   - **Error**: "Entity not found or no longer exists"
   - **Cause**: Entity was removed or doesn't exist
   - **Solution**: Verify entity exists before inspection

**Permission Denied**
   - **Error**: "Permission denied to inspect inventory"
   - **Cause**: Insufficient permissions
   - **Solution**: Check agent permissions

**Network Error**
   - **Error**: "Network error during inventory inspection"
   - **Cause**: Communication failure with game server
   - **Solution**: Retry the operation

Related Tools
-------------

- :doc:`insert_item` - Place items into inventories
- :doc:`extract_item` - Remove items from inventories
- :doc:`get_entities` - Find entities with inventories
- :doc:`place_entity` - Place entities with storage
