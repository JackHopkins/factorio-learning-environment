#!/usr/bin/env python3
"""
PostToolUse hook to update overlay after MCP tool invocations.
Reads tool results from stdin and triggers overlay update.
"""

import sys
import json
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/factorio_overlay_hook.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

def main():
    """Process PostToolUse hook data and trigger overlay update."""
    try:
        # Read the hook input from stdin
        input_data = sys.stdin.read()
        hook_data = json.loads(input_data)
        
        tool_name = hook_data.get('toolName', '')
        logger.info(f"PostToolUse hook triggered for tool: {tool_name}")
        
        # Only process certain MCP tools
        relevant_tools = ['execute', 'get_game_state', 'connect', 'get_production_stats']
        if tool_name not in relevant_tools:
            logger.info(f"Ignoring tool {tool_name}, not in relevant list")
            return
        
        # Check if overlay is running by trying to connect
        try:
            # Try to trigger a game state update via the bridge server
            response = requests.get('http://localhost:8000/trigger-update', timeout=1)
            logger.info(f"Triggered overlay update, response: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not reach overlay bridge server: {e}")
            # Optionally try to start it if needed
        
        # For get_game_state results, we could parse and send specific data
        if tool_name == 'get_game_state' and 'result' in hook_data:
            try:
                # The game state might be in the result
                result = hook_data.get('result', {})
                if isinstance(result, dict) and 'inventory' in result:
                    # Could send specific update to overlay
                    logger.info(f"Game state update detected with {len(result.get('inventory', {}))} inventory items")
            except Exception as e:
                logger.error(f"Error processing game state: {e}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse hook input: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in hook: {e}")

if __name__ == "__main__":
    main()