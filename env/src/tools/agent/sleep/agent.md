# sleep

## Overview
The `sleep` tool provides a way to pause execution for a specified duration. It's particularly useful when waiting for game actions to complete, such as waiting for items to be crafted or resources to be gathered.

## Function Signature
```python
def sleep(seconds: int) -> bool
```

### Parameters
- `seconds`: Number of seconds to pause execution (integer)

### Returns
- `bool`: True if sleep completed successfully

## Usage Example
```python
# Wait for 10 seconds
game.sleep(10)

# Wait for furnace to smelt items
furnace = place_entity(Prototype.StoneFurnace, position=Position(0, 0))
insert_item(Prototype.IronOre, furnace, 10)
sleep(5)  # Wait for smelting to complete
```

## Key Behaviors
- Converts real-time seconds to game ticks (60 ticks = 1 second)
- Adapts to game speed settings automatically
- Uses efficient polling to minimize resource usage
- Maximum sleep duration is 15 seconds

## Notes
- Sleep duration is relative to game speed
- Should be used sparingly and only when necessary
- Useful for synchronizing automated processes