#!/bin/bash
# Hook to start the Factorio overlay server when Claude Code session starts

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(dirname $(dirname "$SCRIPT_DIR"))}"

# Log file for debugging
LOG_FILE="/tmp/factorio_overlay_hook.log"

echo "[$(date)] SessionStart hook triggered" >> "$LOG_FILE"
echo "[$(date)] Project root: $PROJECT_ROOT" >> "$LOG_FILE"

# Check if overlay is already running
if pgrep -f "overlay.py" > /dev/null; then
    echo "[$(date)] Overlay already running" >> "$LOG_FILE"
else
    echo "[$(date)] Starting overlay server..." >> "$LOG_FILE"
    
    # Start the overlay server in the background
    cd "$PROJECT_ROOT"
    nohup python fle/overlay.py --port 8081 > /tmp/factorio_overlay.log 2>&1 &
    OVERLAY_PID=$!
    
    echo "[$(date)] Overlay started with PID: $OVERLAY_PID" >> "$LOG_FILE"
    
    # Save PID for later cleanup
    echo $OVERLAY_PID > /tmp/factorio_overlay.pid
    
    # Give it a moment to start
    sleep 2
    
    # Open the overlay in browser (optional - comment out if you don't want auto-open)
    # open "http://localhost:8081"
fi

echo "[$(date)] Hook completed" >> "$LOG_FILE"