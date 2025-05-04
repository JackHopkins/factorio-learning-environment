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
