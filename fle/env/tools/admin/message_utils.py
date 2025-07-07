import os
from typing import List, Dict

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)


def log_messages(messages: List[Dict]) -> None:
    """
    Log messages to a file sorted by timestamp.
    :param messages: List of message dictionaries containing sender, message, timestamp
    """
    # Sort messages by timestamp
    sorted_messages = sorted(messages, key=lambda x: x["timestamp"])

    # ANSI color codes
    ORANGE = "\033[33m"
    GREEN = "\033[32m"
    BLUE = "\033[34m"
    RESET = "\033[0m"

    # Write messages to file
    with open(os.path.join(ROOT_DIR, "message_log.txt"), "w") as f:
        for msg in sorted_messages:
            if msg["sender"] == -1:
                agent_name = "Leader"
                colored_name = f"{ORANGE}{agent_name}{RESET}"
            elif msg["sender"] == 0:
                agent_name = f"Agent {msg['sender']}"
                colored_name = f"{GREEN}{agent_name}{RESET}"
            elif msg["sender"] == 1:
                agent_name = f"Agent {msg['sender']}"
                colored_name = f"{BLUE}{agent_name}{RESET}"
            else:
                agent_name = f"Agent {msg['sender']}"
                colored_name = agent_name

            f.write(f"{colored_name}: {msg['message']}\n\n")


def deduplicate_broadcast_messages(messages):
    """Helper function to deduplicate broadcast messages while preserving direct messages"""
    seen_broadcasts = set()
    deduplicated = []
    for msg in messages:
        msg_key = (msg["sender"], msg["message"])
        if msg_key not in seen_broadcasts:
            seen_broadcasts.add(msg_key)
            deduplicated.append(msg)
    return deduplicated
