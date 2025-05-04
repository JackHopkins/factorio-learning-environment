## How to check research progress

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
s