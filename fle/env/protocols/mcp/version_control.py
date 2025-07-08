"""
Version control tools for Factorio Learning Environment

Provides functionality for managing game state versions, including:
- Committing game states
- Tagging states for easy reference
- Restoring to previous states
- Viewing commit history
"""

from mcp.server.fastmcp import Context
from fle.commons.models.game_state import GameState
from fle.env.protocols.mcp import mcp
from fle.env.protocols.mcp.init import state


@mcp.tool()
async def undo(ctx: Context) -> str:
    """
    Undo the last code execution by restoring the previous state
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    prev_commit_id = vcs.undo()
    if not prev_commit_id:
        return "Nothing to undo. Already at initial state."

    # Apply the previous state
    success = vcs.apply_to_instance(prev_commit_id)

    if success:
        return f"Undid last operation. Restored to commit {prev_commit_id[:8]}"
    else:
        return "Failed to restore previous state"


@mcp.tool()
async def commit(ctx: Context, tag_name: str, message: str = None) -> str:
    """
    Tag the current commit with a name for easier reference

    Args:
        tag_name: Name to give this checkpoint
        message: Optional message to describe this checkpoint
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    commit_id = vcs.tag_commit(tag_name)

    if message:
        # Create a new commit with the custom message instead of just tagging
        current_state = GameState.from_instance(state.active_server)
        policy = vcs.get_policy(commit_id)
        commit_id = vcs.commit(current_state, message, policy)
        vcs.tag_commit(tag_name, commit_id)

    return f"Tagged current state as '{tag_name}' (commit {commit_id[:8]})"


@mcp.tool()
async def restore(ctx: Context, ref: str) -> str:
    """
    Restore to a previous tagged state or commit ID

    Args:
        ref: Tag name or commit ID (can be abbreviated)
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    # First check if it's a tag
    tag_commit = vcs.get_tag(ref)
    if tag_commit:
        commit_id = tag_commit
    else:
        # If abbreviated ID, try to find a match
        if len(ref) < 40:
            history = vcs.get_history(max_count=100)
            for commit in history:
                if commit["id"].startswith(ref):
                    commit_id = commit["id"]
                    break
            else:
                return f"No commit found matching '{ref}'"
        else:
            commit_id = ref

    try:
        # Apply the state
        success = vcs.apply_to_instance(commit_id)

        if success:
            # Update HEAD and undo stack
            vcs.checkout(commit_id)
            return f"Successfully restored to {ref} (commit {commit_id[:8]})"
        else:
            return f"Failed to restore: no state data in commit {commit_id[:8]}"
    except Exception as e:
        return f"Error restoring checkpoint: {str(e)}"


@mcp.tool()
async def view_history(ctx: Context, limit: int = 10) -> str:
    """
    View commit history of game states

    Args:
        limit: Maximum number of commits to show
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    history = vcs.get_history(max_count=limit)
    tags = vcs.list_tags()

    # Create reverse mapping of commit IDs to tag names
    commit_to_tags = {}
    for tag_name, commit_id in tags.items():
        if commit_id not in commit_to_tags:
            commit_to_tags[commit_id] = []
        commit_to_tags[commit_id].append(tag_name)

    if not history:
        return "No commit history found."

    result = "Checkpoint History:\n"
    for i, commit in enumerate(history):
        commit_id = commit["id"]
        short_id = commit_id[:8]
        has_policy = "✓" if commit["has_policy"] else " "

        # Add any tags for this commit
        tag_str = ""
        if commit_id in commit_to_tags:
            tag_str = f" [{', '.join(commit_to_tags[commit_id])}]"

        result += f"{i + 1}. [{short_id}]{tag_str} {has_policy} {commit['message']}\n"

    return result


@mcp.tool()
async def list_tags(ctx: Context) -> str:
    """List all named checkpoints"""
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    tags = vcs.list_tags()

    if not tags:
        return "No tags found."

    result = "Named Checkpoints:\n"
    for tag_name, commit_id in tags.items():
        result += f"{tag_name}: {commit_id[:8]}\n"

    return result


@mcp.tool()
async def view_code(ctx: Context, ref: str) -> str:
    """
    View the code associated with a commit or tag

    Args:
        ref: Tag name or commit ID
    """
    if not state.active_server:
        return "No active Factorio server connection. Use connect first."

    vcs = state.get_vcs()
    if not vcs:
        return "VCS not initialized. Please connect to a server first."

    # First check if it's a tag
    if ref in vcs.list_tags():
        commit_id = vcs.get_tag(ref)
    else:
        # If abbreviated ID, try to find a match
        if len(ref) < 40:
            history = vcs.get_history(max_count=100)
            for commit in history:
                if commit["id"].startswith(ref):
                    commit_id = commit["id"]
                    break
            else:
                return f"No commit found matching '{ref}'"
        else:
            commit_id = ref

    # Get the policy (code) for this commit
    policy = vcs.get_policy(commit_id)

    if not policy:
        return f"No code found for {ref} (commit {commit_id[:8]})"

    return f"Code for {ref} (commit {commit_id[:8]}):\n\n```python\n{policy}\n```"
