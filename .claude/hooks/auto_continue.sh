#!/bin/bash
# Hook to automatically respond with "Continue" on certain notifications

# Read the hook input from stdin
INPUT=$(cat)

# Log file for debugging
LOG_FILE="/tmp/factorio_overlay_hook.log"

# Log the raw input for debugging
echo "[$(date)] Notification hook triggered" >> "$LOG_FILE"
echo "[$(date)] Raw input: $INPUT" >> "$LOG_FILE"

# Parse the notification using jq (more reliable)
if command -v jq &> /dev/null; then
    # Extract relevant fields
    NOTIFICATION_TYPE=$(echo "$INPUT" | jq -r '.notificationType // .type // "unknown"')
    MESSAGE=$(echo "$INPUT" | jq -r '.message // .content // ""')
    TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')

    echo "[$(date)] Parsed - Type: $NOTIFICATION_TYPE, Message: $MESSAGE, Tool: $TOOL_NAME" >> "$LOG_FILE"

    # Check various conditions for auto-continue
    # Claude Code might send different notification structures
    if echo "$MESSAGE" | grep -iE "(continue|proceed|waiting|ready)" > /dev/null 2>&1; then
        echo "[$(date)] Auto-continuing based on message content" >> "$LOG_FILE"
        # Return proper JSON response for Claude Code
        echo '{"action": "continue", "response": "Continue"}'
        exit 0
    fi

    # Check for specific notification types
    case "$NOTIFICATION_TYPE" in
        "user_input_required"|"confirmation_needed"|"ready_for_next_step")
            echo "[$(date)] Auto-continuing for notification type: $NOTIFICATION_TYPE" >> "$LOG_FILE"
            echo '{"action": "continue", "response": "Continue"}'
            exit 0
            ;;
        *)
            # Log but don't auto-continue
            echo "[$(date)] Not auto-continuing for type: $NOTIFICATION_TYPE" >> "$LOG_FILE"
            ;;
    esac
else
    echo "[$(date)] jq not found, using fallback parsing" >> "$LOG_FILE"

    # Fallback: simple pattern matching
    if echo "$INPUT" | grep -iE "(continue|waiting|ready|proceed)" > /dev/null 2>&1; then
        echo "[$(date)] Auto-continuing (fallback mode)" >> "$LOG_FILE"
        echo '{"action": "continue", "response": "Continue"}'
        exit 0
    fi
fi

# If we get here, don't auto-continue
echo "[$(date)] No auto-continue triggered" >> "$LOG_FILE"
# Return empty JSON or no response
echo '{}'