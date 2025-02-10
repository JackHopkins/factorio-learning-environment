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

### 3. Research Queue Management
```python
def manage_research_queue(technologies):
    for tech in technologies:
        try:
            requirements = get_research_progress(tech)
            print(f"Research {tech.name} requires:")
            for req in requirements:
                print(f"- {req.count} {req.name}")
        except Exception as e:
            print(f"Cannot research {tech.name}: {e}")
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

2. **Verify Research Prerequisites**
```python
def verify_research_chain(technology):
    try:
        requirements = get_research_progress(technology)
        if not requirements:
            print("Technology already researched")
            return True
        return check_science_pack_availability(requirements)
    except Exception as e:
        print(f"Error verifying research: {e}")
        return False
```

3. **Track Science Pack Requirements**
```python
def track_science_pack_needs():
    current_needs = {}
    try:
        requirements = get_research_progress()
        for req in requirements:
            current_needs[req.name] = req.count
        return current_needs
    except Exception:
        return {}
```

## Common Patterns

### Research Monitoring System
```python
def monitor_research_system():
    try:
        # Get current research requirements
        requirements = get_research_progress()
        
        # Check lab inventory
        lab = get_entity(Prototype.Lab, lab_position)
        lab_inventory = inspect_inventory(lab)
        
        # Compare requirements vs availability
        for req in requirements:
            available = lab_inventory.get(req.name, 0)
            if available < req.count:
                print(f"Warning: Low on {req.name}")
                
    except Exception as e:
        print(f"Research monitoring error: {e}")
```

### Automated Research Management
```python
def manage_research_automation(tech_queue):
    for tech in tech_queue:
        try:
            # Check requirements
            requirements = get_research_progress(tech)
            
            # Verify science pack production
            if not verify_science_production(requirements):
                print(f"Cannot meet requirements for {tech.name}")
                continue
                
            # Set research if feasible
            set_research(tech)
            
        except Exception as e:
            print(f"Research automation error: {e}")
```

## Error Handling

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

## Tips for Effective Usage

1. **Research State Management**
   - Always check current research state before operations
   - Handle both active and inactive research cases
   - Verify technology prerequisites

2. **Resource Planning**
   - Track science pack requirements
   - Monitor lab inventories
   - Plan production accordingly

3. **Error Recovery**
   - Handle missing research gracefully
   - Provide fallback options
   - Maintain research queue state

## Debugging Tips

If research progress checking fails:

1. **Verify Research Status**
   - Check if technology exists
   - Verify research prerequisites
   - Confirm research is active (if checking current research)

2. **Check Science Pack Production**
   - Verify science pack availability
   - Check lab connections
   - Monitor production chains

3. **Handle Edge Cases**
   - Already researched technologies
   - Invalid technology names
   - Missing prerequisites

## Integration Examples

### Research Progress Monitor
```python
def research_progress_monitor():
    def format_time_estimate(requirements):
        # Estimate time based on science pack counts
        return sum(req.count * 5 for req in requirements)  # 5 seconds per pack
        
    try:
        requirements = get_research_progress()
        if not requirements:
            return "Research complete!"
            
        time_estimate = format_time_estimate(requirements)
        return f"Estimated time remaining: {time_estimate} seconds"
        
    except Exception as e:
        return f"Research monitoring error: {e}"
```

### Automated Lab Management
```python
def manage_labs(lab_positions):
    try:
        requirements = get_research_progress()
        if not requirements:
            return "No research needs"
            
        for lab_pos in lab_positions:
            lab = get_entity(Prototype.Lab, lab_pos)
            if not lab:
                continue
                
            # Check and resupply lab
            lab_inventory = inspect_inventory(lab)
            for req in requirements:
                if lab_inventory.get(req.name, 0) < req.count:
                    # Trigger resupply system
                    pass
                    
    except Exception as e:
        return f"Lab management error: {e}"
```