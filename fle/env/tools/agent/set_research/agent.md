# set_research

## Overview
The `set_research` tool enables setting the current research technology for the player's force in Factorio. It manages research prerequisites, validates technology availability, and provides information about required research ingredients.

## Function Signature
```python
def set_research(technology: Technology) -> List[Ingredient]
```

### Parameters
- `technology`: A Technology enum value representing the technology to research

### Returns
- Returns a list of `Ingredient` objects containing the required science packs and their quantities
- Each `Ingredient` object has:
  - `name`: Name of the required science pack
  - `count`: Number of science packs needed
  - `type`: Type of the ingredient (usually "item" for science packs)

## Usage Example
```python
# Set research to Automation technology
ingredients = set_research(Technology.Automation)

# Check required ingredients
for ingredient in ingredients:
    print(f"Need {ingredient.count} {ingredient.name}")
```

## Key Behaviors
- Cancels any current research before setting new research
- Validates technology prerequisites
- Checks if required science pack recipes are unlocked
- Returns detailed ingredient requirements for the research

## Validation Checks
The tool performs several validation checks before starting research:
1. Verifies the technology exists
2. Confirms the technology isn't already researched
3. Checks if the technology is enabled
4. Validates all prerequisites are researched
5. Ensures required science pack recipes are available

## Error Cases
The tool will raise exceptions in the following situations:
- Technology doesn't exist
- Technology is already researched
- Technology is not enabled
- Missing prerequisites
- Missing required science pack recipes
- Failed to start research

Example error messages:
```python
"Cannot research automation-2 because missing prerequisite: automation"
"Cannot research logistics-2 because technology is not enabled"
```

## Requirements
- The technology must be valid and available
- All prerequisites must be researched
- Required science pack recipes must be unlocked
