# get_research_progress

The `get_research_progress` tool checks the progress of technology research in Factorio by returning the remaining science pack requirements. This tool is essential for managing research queues and monitoring research progress.

## Core Functionality

The tool provides:
- Remaining science pack requirements for a specific technology
- Current research progress if no technology is specified
- Status information about researched/unresearched technologies

## Basic Usage

```python
# Check progress of specific technology
remaining = get_research_progress(Technology.Automation)

# Check current research progress
current_progress = get_research_progress()  # Only works if research is active!
```

### Parameters

- `technology`: Optional[Technology] - The technology to check progress for
  - If provided: Returns remaining requirements for that technology
  - If None: Returns requirements for current research (must have active research!)

### Return Value

Returns a List[Ingredient] where each Ingredient contains:
- name: Name of the science pack
- count: Number of packs still needed
- type: Type of the ingredient (usually "item" for science packs)

## Important Notes

1. **Current Research Check**
   ```python
   try:
       progress = get_research_progress()
   except Exception as e:
       print("No active research!")
       # Handle no research case
   ```

2. **Research Status Verification**
   ```python
   try:
       # Check specific technology
       progress = get_research_progress(Technology.Automation)
   except Exception as e:
       print(f"Cannot check progress: {e}")
       # Handle invalid technology case
   ```

## Common Use Cases

### 1. Monitor Current Research
```python
def monitor_research_progress():
    try:
        remaining = get_research_progress()
        for ingredient in remaining:
            print(f"Need {ingredient.count} {ingredient.name}")
    except Exception:
        print("No research in progress")
```

### 2. Research Requirements Planning
```python
def check_research_feasibility(technology):
    try:
        requirements = get_research_progress(technology)
        inventory = inspect_inventory()
        
        for req in requirements:
            if inventory[req.name] < req.count:
                print(f"Insufficient {req.name}: have {inventory[req.name]}, need {req.count}")
                return False
        return True
    except Exception as e:
        print(f"Error checking research: {e}")
        return False
```

## Best Practices

1. **Always Handle No Research Case**
```python
def safe_get_progress():
    try:
        return get_research_progress()
    except Exception:
        # No research in progress
        return None
```

### Common Errors

1. **No Active Research**
```python
try:
    progress = get_research_progress()
except Exception as e:
    if "No research in progress" in str(e):
        # Handle no research case
        pass
```

2. **Invalid Technology**
```python
try:
    progress = get_research_progress(technology)
except Exception as e:
    if "Technology doesn't exist" in str(e):
        # Handle invalid technology case
        pass
```

3. **Already Researched**
```python
if not get_research_progress(technology):
    print("Technology already researched")
```
