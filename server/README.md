# Factorio Learning Environment MCP Server

The Factorio Learning Environment (FLE) MCP Server provides a standardized interface for AI agents to interact with Factorio game servers using the Model Context Protocol (MCP).

## Features

- Connect to running Factorio servers
- Execute Python code in the Factorio environment
- Retrieve game state, entities, and resources
- Render the factory state as an image
- Version control for game states with commit, restore, and undo functionality
- Access to recipes and crafting information

## Installation

### Requirements

- Python 3.10+
- MCP SDK (installed via `pip install mcp[cli]`)
- Factorio game (the environment will connect to running servers)

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the Server

You can start the server with either stdio transport (for use with Claude Desktop or other MCP clients) or SSE transport:

```bash
# Start with stdio transport (default)
python server.py

# Start with SSE transport
python server.py --transport sse --host 127.0.0.1 --port 3000
```

### Installing in Claude Desktop

```bash
mcp install server.py
```

## Resources

The server exposes various resources that provide information about the Factorio game state:

- `fle://servers` - List of available Factorio servers
- `fle://server/{instance_id}/entities` - All entities on a specific server
- `fle://server/{instance_id}/entities/{top_left_x}/{top_left_y}/{bottom_right_x}/{bottom_right_y}` - Entities in a specified area
- `fle://server/{instance_id}/resources/{name}` - Resource patches of a specific type
- `fle://recipes` - All available recipes
- `fle://recipe/{name}` - Details for a specific recipe
- `fle://api/docs/{method}` - API documentation for a specific method
- `fle://api/schema` - Complete API schema

## Tools

The server provides the following tools:

### Factorio Game Interaction

- `render(center_x, center_y)` - Render the current factory state to an image
- `execute(code)` - Run Python code in the Factorio environment
- `connect(instance_id)` - Connect to a Factorio server
- `status()` - Check the status of the Factorio server connection

### Version Control

Tools for managing game state versions (in `version_control.py`):
- `commit(tag_name, message)` - Tag the current state
- `restore(ref)` - Restore to a previous tagged state
- `undo()` - Undo the last operation
- `view_history(limit)` - View commit history
- `list_tags()` - List all named checkpoints
- `view_code(ref)` - View the code associated with a commit

### Recipe Management

- `get_recipe(name)` - Get details for a specific recipe
- `get_all_recipes()` - Get all available recipes

### Documentation

- `manual(name)` - Get API documentation for a specific method
- `schema()` - Get the full API object model

### Unix-like Tools for Code Introspection

These tools help agents explore and understand the codebase:

- `ls(path, pattern)` - List tools and directories in the tools path
- `cat(file_path)` - Display the contents of a file
- `find(path, name_pattern, content_pattern, type_filter, max_depth)` - Find files or directories 
- `grep(pattern, path, recursive, case_sensitive, line_numbers)` - Search for a pattern in files
- `which(command)` - Find the implementation file for a specific Factorio tool
- `head(file_path, lines)` - Display the first lines of a file
- `tail(file_path, lines)` - Display the last lines of a file
- `tree(path, max_depth)` - Display directory structure in a tree-like format
- `man(command)` - Display the manual/documentation for a Factorio tool
- `whereis(keyword)` - Find all occurrences related to a keyword
- `diff(file1, file2)` - Compare two files and show the differences

## Lifecycle

The server follows this lifecycle:

1. Initialize the MCP server when a new session begins
2. Scan for running Factorio servers
3. Automatically connect to the first active server found
4. Clean up resources when the session ends

## Development

To extend the server with new tools or resources:

1. Add new tool functions in `tools.py` using the `@mcp.tool()` decorator
2. Add new resources in `resources.py` using the `@mcp.resource()` decorator
3. Update state management in `state.py` if needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.