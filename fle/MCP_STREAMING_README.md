# MCP Streaming Setup for Factorio Learning Environment

This setup allows you to view real-time Factorio game state from Claude Code in a separate overlay window.

## Architecture

```
Claude Code (MCP Server) → State File → Bridge Server → WebSocket → Overlay UI
```

## Components

1. **MCP Server** (`fle_mcp_server.py`) - Running in Claude Code
   - Provides tools like `execute()`, `get_game_state()`, etc.
   - Writes game state to `/tmp/factorio_game_state.json` after each action

2. **Bridge Server** (`simple_bridge.py`) - Standalone process
   - Monitors the state file for changes
   - Provides WebSocket and SSE endpoints for real-time updates
   - Runs on port 8000 by default

3. **Overlay UI** (`simple_overlay.py`) - Viewer application  
   - Connects to bridge server via WebSocket
   - Displays game state in a compact overlay window
   - Runs on port 8081 by default

## Quick Start

1. **Start the bridge server** (in a terminal):
   ```bash
   python fle/simple_bridge.py
   ```

2. **Start the overlay UI** (in another terminal):
   ```bash
   python fle/simple_overlay.py
   ```

3. **In Claude Code**, use the MCP server normally:
   - Connect to a Factorio server
   - Execute commands with `execute()` tool
   - Call `get_game_state()` to update the display

The overlay will automatically update whenever the game state changes.

## How It Works

1. When you run `execute()` or `get_game_state()` in Claude Code, the MCP server writes the current game state to `/tmp/factorio_game_state.json`

2. The bridge server polls this file every 100ms and sends updates to connected WebSocket clients

3. The overlay UI receives these updates and displays:
   - Connection status
   - Current score
   - Game tick
   - Player position
   - Top inventory items
   - Entity count

## Advanced Usage

### Custom Bridge URL
```bash
python fle/simple_overlay.py --bridge-url ws://localhost:8000/ws
```

### Different Ports
```bash
# Bridge server on custom port
python fle/simple_bridge.py  # (modify port in code)

# Overlay on custom port
python fle/simple_overlay.py --port 8082
```

### Debugging

Check bridge server status:
```bash
curl http://localhost:8000/status
```

View current game state:
```bash
curl http://localhost:8000/state
```

Monitor state file:
```bash
watch -n 1 cat /tmp/factorio_game_state.json | jq .
```

## Troubleshooting

1. **No updates showing**: 
   - Make sure you've connected to a Factorio server in Claude Code
   - Check that `/tmp/factorio_game_state.json` exists
   - Verify bridge server is running

2. **Connection errors**:
   - Check that both servers are running on the expected ports
   - Look for firewall issues if running on different machines

3. **State not updating**:
   - Call `get_game_state()` manually in Claude Code
   - Check bridge server logs for errors