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
    # Extract relevant fields - include hook_event_name for Claude Code
    NOTIFICATION_TYPE=$(echo "$INPUT" | jq -r '.notificationType // .type // .hook_event_name // "unknown"')
    MESSAGE=$(echo "$INPUT" | jq -r '.message // .content // ""')
    TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // ""')
    HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // ""')

    echo "[$(date)] Parsed - Type: $NOTIFICATION_TYPE, Message: $MESSAGE, Tool: $TOOL_NAME" >> "$LOG_FILE"

    # Check various conditions for auto-continue
    # Check for factorio agent completion or Claude waiting
    if echo "$MESSAGE" | grep -iE "(factorio.*complete|agent.*stopped|observation.*ready|Claude is waiting)" > /dev/null 2>&1; then
        echo "[$(date)] Auto-continuing based on factorio agent or waiting message" >> "$LOG_FILE"
        echo '{"action": "continue", "response": "Continue"}'
        exit 0
    fi
    
    # Check for standard continue patterns
    if echo "$MESSAGE" | grep -iE "(continue|proceed|waiting|ready)" > /dev/null 2>&1; then
        echo "[$(date)] Auto-continuing based on message content" >> "$LOG_FILE"
        echo '{"action": "continue", "response": "Continue"}'
        exit 0
    fi
    
    # Check if it's a Notification event from Claude Code
    if [ "$HOOK_EVENT" = "Notification" ] && echo "$MESSAGE" | grep -iE "waiting" > /dev/null 2>&1; then
        echo "[$(date)] Auto-continuing for Claude Code notification with waiting" >> "$LOG_FILE"
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