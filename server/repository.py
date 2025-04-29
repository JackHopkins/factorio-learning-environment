import time
from typing import Dict, List, Optional, Tuple, Any

from dulwich.objects import Blob, Tree, Commit
from dulwich.repo import MemoryRepo

from env.src.instance import FactorioInstance
from env.src.models.game_state import GameState


class FactorioMCPRepository:

    """Version control system for Factorio game states using Dulwich"""

    def __init__(self, instance: FactorioInstance):
        self.repo = MemoryRepo()
        self.branch = b"refs/heads/main"
        self.current_branch = "main"
        self.instance = instance
        self.branches = {"main": None}
        self.tags = {}  # Named commits for quick reference
        self.undo_stack = []  # Stack of commit IDs for undo operations

        # Initialize with empty state
        self._init_repo()

    def _init_repo(self):
        """Initialize the repository with an empty commit"""
        initial_state = GameState.from_instance(self.instance)
        self.commit(initial_state, "Initial state", None)

    def _make_blob(self, data: str) -> Tuple[bytes, Blob]:
        """Create a blob object from string data"""
        blob = Blob.from_string(data.encode('utf-8'))
        self.repo.object_store.add_object(blob)
        return blob.id, blob

    def _make_tree(self, entries: Dict[str, Tuple[int, bytes]]) -> Tuple[bytes, Tree]:
        """Create a tree object from a dictionary of entries"""
        tree = Tree()
        for name, (mode, blob_id) in entries.items():
            tree.add(name.encode('utf-8'), mode, blob_id)
        self.repo.object_store.add_object(tree)
        return tree.id, tree

    def commit(self, state: GameState, message: str, policy: Optional[str] = None) -> str:
        """Create a commit with the given state and message"""
        # Create blobs for state and policy
        state_id, state_blob = self._make_blob(state.to_raw())

        # Create tree entries
        entries = {
            "gamestate.json": (0o100644, state_id)
        }

        if policy:
            policy_id, policy_blob = self._make_blob(policy)
            entries["policy.py"] = (0o100644, policy_id)

        # Create tree
        tree_id, tree = self._make_tree(entries)

        # Create commit
        commit = Commit()
        commit.tree = tree_id
        commit.author = commit.committer = b"FLE-Agent <agent@fle.local>"
        commit.commit_time = commit.author_time = int(time.time())
        commit.commit_timezone = commit.author_timezone = 0
        commit.message = message.encode('utf-8')

        # Add parent if exists
        try:
            if self.branch in self.repo.refs:
                commit.parents = [self.repo.refs[self.branch]]
        except Exception:
            # No parent, this is the first commit
            pass

        self.repo.object_store.add_object(commit)

        # Update HEAD and branch reference
        commit_id = commit.id.decode('utf-8')
        self.repo.refs[self.branch] = commit.id
        self.branches[self.current_branch] = commit_id

        # Add to undo stack
        self.undo_stack.append(commit_id)

        return commit_id

    def tag_commit(self, name: str, commit_id: Optional[str] = None) -> str:
        """Create a named tag for a commit (default: current HEAD)"""
        if commit_id is None:
            try:
                if self.branch in self.repo.refs:
                    commit_id = self.repo.refs[self.branch].decode('utf-8')
                else:
                    raise ValueError("No current HEAD to tag")
            except Exception as e:
                raise ValueError(f"Error getting current HEAD: {str(e)}")

        self.tags[name] = commit_id
        return commit_id

    def get_tag(self, name: str) -> Optional[str]:
        """Get commit ID for a named tag"""
        return self.tags.get(name)

    def list_tags(self) -> Dict[str, str]:
        """List all tags and their commit IDs"""
        return self.tags

    def checkout(self, ref: str) -> str:
        """
        Checkout a specific commit, branch, or tag.
        This only changes internal state - doesn't affect the game instance.
        """
        # Check if it's a tag
        if ref in self.tags:
            ref = self.tags[ref]

        # Handle branch name
        if ref in self.branches:
            self.current_branch = ref
            self.branch = f"refs/heads/{ref}".encode('utf-8')
            try:
                if self.branch in self.repo.refs:
                    commit_id = self.repo.refs[self.branch]
                else:
                    return None
            except Exception:
                return None
        else:
            # Handle commit ID
            commit_id = ref.encode('utf-8') if isinstance(ref, str) else ref
            # Detached HEAD state
            self.current_branch = None

        return commit_id.decode('utf-8') if commit_id else None

    def apply_to_instance(self, commit_id: Optional[str] = None) -> bool:
        """Apply a specific commit to the game instance"""
        if commit_id is None:
            # Use current HEAD
            try:
                if self.branch in self.repo.refs:
                    commit_id = self.repo.refs[self.branch]
                else:
                    raise ValueError("No current commit to apply")
            except Exception as e:
                raise ValueError(f"Error getting current HEAD: {str(e)}")
        else:
            commit_id = commit_id.encode('utf-8') if isinstance(commit_id, str) else commit_id

        try:
            # Get the commit
            commit = self.repo.object_store[commit_id]
            # Get the tree
            tree = self.repo.object_store[commit.tree]
            # Get the state blob
            if b"gamestate.json" in tree:
                state_id = tree[b"gamestate.json"][1]
                state_blob = self.repo.object_store[state_id]
                state_json = state_blob.data.decode('utf-8')

                # Parse and apply state
                state = GameState.parse_raw(state_json)
                self.instance.reset(game_state=state)
                return True
        except Exception as e:
            print(f"Error applying commit {commit_id}: {str(e)}")

        return False

    def undo(self) -> Optional[str]:
        """
        Undo to the previous commit.
        Returns the commit ID that was restored, or None if no more history.
        """
        if len(self.undo_stack) <= 1:
            return None  # Nothing to undo

        # Remove current commit from stack
        self.undo_stack.pop()

        # Get previous commit
        if not self.undo_stack:
            return None

        prev_commit_id = self.undo_stack[-1]

        # Update HEAD reference
        commit_id_bytes = prev_commit_id.encode('utf-8')
        self.repo.refs[self.branch] = commit_id_bytes
        self.branches[self.current_branch] = prev_commit_id

        return prev_commit_id

    def get_policy(self, commit_id: str) -> Optional[str]:
        """Get the policy associated with a commit"""
        commit_id = commit_id.encode('utf-8') if isinstance(commit_id, str) else commit_id

        try:
            commit = self.repo.object_store[commit_id]
            tree = self.repo.object_store[commit.tree]

            if b"policy.py" in tree:
                policy_id = tree[b"policy.py"][1]
                policy_blob = self.repo.object_store[policy_id]
                return policy_blob.data.decode('utf-8')
        except KeyError:
            pass

        return None

    def get_history(self, max_count=10) -> List[Dict[str, Any]]:
        """Get commit history"""
        history = []
        try:
            if self.branch not in self.repo.refs:
                return history

            commit_id = self.repo.refs[self.branch]

            while commit_id and len(history) < max_count:
                try:
                    commit = self.repo.object_store[commit_id]
                    history.append({
                        "id": commit_id.decode('utf-8'),
                        "message": commit.message.decode('utf-8'),
                        "timestamp": commit.commit_time,
                        "has_policy": self._has_policy(commit.tree)
                    })

                    if commit.parents:
                        commit_id = commit.parents[0]
                    else:
                        break
                except KeyError:
                    break
        except Exception as e:
            print(f"Error getting history: {str(e)}")

        return history

    def _has_policy(self, tree_id):
        """Check if a tree contains a policy file"""
        try:
            tree = self.repo.object_store[tree_id]
            return b"policy.py" in tree
        except Exception:
            return False

    def diff_policies(self, commit_id1: str, commit_id2: str) -> Dict[str, Any]:
        """
        Compare policies between two commits.
        Returns information about the differences.
        """
        try:
            policy1 = self.get_policy(commit_id1)
            policy2 = self.get_policy(commit_id2)

            if policy1 is None and policy2 is None:
                return {"status": "no_policies", "message": "Neither commit has a policy"}

            if policy1 is None:
                return {
                    "status": "added",
                    "message": "Policy added in second commit",
                    "policy": policy2
                }

            if policy2 is None:
                return {
                    "status": "removed",
                    "message": "Policy removed in second commit",
                    "policy": policy1
                }

            # Both commits have policies, compute line-based diff
            import difflib
            diff = list(difflib.unified_diff(
                policy1.splitlines(keepends=True),
                policy2.splitlines(keepends=True),
                fromfile=f"policy-{commit_id1[:8]}.py",
                tofile=f"policy-{commit_id2[:8]}.py"
            ))

            return {
                "status": "modified",
                "message": "Policy modified between commits",
                "diff": "".join(diff),
                "policy1": policy1,
                "policy2": policy2
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error comparing policies: {str(e)}"
            }