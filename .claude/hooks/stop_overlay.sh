#!/bin/bash
# Hook to stop the Factorio overlay server when Claude Code session ends

LOG_FILE="/tmp/factorio_overlay_hook.log"
PID_FILE="/tmp/factorio_overlay.pid"

echo "[$(date)] SessionEnd hook triggered" >> "$LOG_FILE"

# Check if PID file exists
if [ -f "$PID_FILE" ]; then
    OVERLAY_PID=$(cat "$PID_FILE")
    echo "[$(date)] Found overlay PID: $OVERLAY_PID" >> "$LOG_FILE"
    
    # Check if process is still running
    if ps -p $OVERLAY_PID > /dev/null 2>&1; then
        echo "[$(date)] Stopping overlay server..." >> "$LOG_FILE"
        kill $OVERLAY_PID
        
        # Give it a moment to stop gracefully
        sleep 2
        
        # Force kill if still running
        if ps -p $OVERLAY_PID > /dev/null 2>&1; then
            echo "[$(date)] Force killing overlay server..." >> "$LOG_FILE"
            kill -9 $OVERLAY_PID
        fi
    else
        echo "[$(date)] Overlay process not found" >> "$LOG_FILE"
    fi
    
    # Clean up PID file
    rm -f "$PID_FILE"
else
    echo "[$(date)] No PID file found" >> "$LOG_FILE"
fi

# Also try to kill by process name as backup
pkill -f "overlay.py" >> "$LOG_FILE" 2>&1

echo "[$(date)] SessionEnd hook completed" >> "$LOG_FILE"