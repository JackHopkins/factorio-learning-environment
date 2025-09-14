# Claude Code Hooks for Factorio Learning Environment

This directory contains hooks that automatically integrate the Factorio overlay with Claude Code sessions.

## Hooks Overview

### SessionStart Hook (`start_overlay.sh`)
- **Trigger**: When a new Claude Code session starts in this project
- **Action**: Launches the Factorio overlay server on port 8081
- **Features**:
  - Checks if overlay is already running to avoid duplicates
  - Logs output to `/tmp/factorio_overlay.log`
  - Saves PID for clean shutdown

### PostToolUse Hook (`update_overlay.py`)
- **Trigger**: After any MCP tool from factorio-learning-env is used
- **Action**: Notifies the overlay to refresh its display
- **Monitors**: Tools like `execute`, `get_game_state`, `connect`, `get_production_stats`

### Notification Hook (`auto_continue.sh`)
- **Trigger**: On specific Claude Code notifications
- **Action**: Automatically responds with "Continue" to keep workflows running
- **Note**: Currently configured for basic notifications, can be customized

### SessionEnd Hook (`stop_overlay.sh`)
- **Trigger**: When Claude Code session ends
- **Action**: Cleanly shuts down the overlay server
- **Features**:
  - Graceful shutdown with fallback to force kill
  - Cleans up PID files

## Usage

These hooks are automatically activated when you start a Claude Code session in this project. No manual intervention is needed.

### Viewing the Overlay
Once the session starts, the overlay will be available at:
- http://localhost:8081

### Debugging
Check logs at:
- Hook logs: `/tmp/factorio_overlay_hook.log`
- Overlay server logs: `/tmp/factorio_overlay.log`

### Manual Control
If you need to manually control the overlay:
```bash
# Start overlay manually
python fle/overlay.py --port 8081

# Stop overlay manually
pkill -f "overlay.py"
```

## Configuration

Hooks are configured in `.claude/settings.json`. You can:
- Modify the `matcher` patterns to control when hooks trigger
- Add additional hooks for other events
- Change commands or add parameters

## Troubleshooting

1. **Overlay doesn't start**: Check `/tmp/factorio_overlay_hook.log` for errors
2. **Port already in use**: The start script checks for existing processes
3. **Hooks not triggering**: Ensure `.claude/settings.json` is properly formatted
4. **Updates not showing**: Verify the MCP bridge server is running