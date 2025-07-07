import os
import time
from typing import Dict, List, Optional, Tuple, Any

from dulwich.objects import Blob, Tree, Commit
from dulwich.repo import Repo

from fle.env import FactorioInstance
from fle.commons.models.game_state import GameState


class FactorioMCPRepository:
    """Version control system for Factorio game states using Dulwich"""

    def __init__(self, instance: FactorioInstance):
        # Create a directory for storing the repository in the current working directory
        self.repo_dir = os.path.abspath(os.path.join(os.getcwd(), ".factorio_mcp_repo"))
        os.makedirs(self.repo_dir, exist_ok=True)

        # Create instance-specific repo directory
        instance_id = instance.tcp_port
        self.instance_repo_dir = os.path.join(self.repo_dir, f"instance_{instance_id}")
        os.makedirs(self.instance_repo_dir, exist_ok=True)

        # Initialize repository (either from disk or create new)
        if os.path.exists(os.path.join(self.instance_repo_dir, ".git")):
            self.repo = Repo(self.instance_repo_dir)
        else:
            # Initialize a new repo
            self.repo = Repo.init(self.instance_repo_dir)

        self.branch = b"refs/heads/main"
        self.current_branch = "main"
        self.instance = instance
        self.branches = {"main": None}
        self.tags = {}  # Named commits for quick reference
        self.undo_stack = []  # Stack of commit IDs for undo operations

        # Initialize repo if needed
        if not self._has_commits():
            self._init_repo()
        else:
            # Load existing state
            self._load_existing_state()

    def _has_commits(self):
        """Check if the repository has any commits"""
        try:
            refs_dict = self.repo.refs.as_dict()
            return self.branch in refs_dict
        except Exception as e:
            print(f"Error checking for commits: {str(e)}")
            return False

    def _load_existing_state(self):
        """Load existing state from disk repository"""
        try:
            # Load branches using proper refs iteration
            refs_dict = self.repo.refs.as_dict()
            for ref_name, ref_value in refs_dict.items():
                if ref_name.startswith(b"refs/heads/"):
                    branch_name = ref_name.decode("utf-8").replace("refs/heads/", "")
                    self.branches[branch_name] = ref_value.decode("utf-8")
                elif ref_name.startswith(b"refs/tags/"):
                    tag_name = ref_name.decode("utf-8").replace("refs/tags/", "")
                    self.tags[tag_name] = ref_value.decode("utf-8")

            # Initialize undo stack with commit history
            if self.branch in refs_dict:
                history = self.get_history(max_count=100)
                self.undo_stack = [commit["id"] for commit in history]
        except Exception as e:
            print(f"Error loading existing repository state: {str(e)}")
            # Provide fallback to prevent startup failure
            if not self.branches:
                self.branches = {"main": None}

    def _init_repo(self):
        """Initialize the repository with an empty commit"""
        initial_state = GameState.from_instance(self.instance)
        self.commit(initial_state, "Initial state", None)

    def _make_blob(self, data: str) -> Tuple[bytes, Blob]:
        """Create a blob object from string data"""
        blob = Blob.from_string(data.encode("utf-8"))
        self.repo.object_store.add_object(blob)
        return blob.id, blob

    def _make_tree(self, entries: Dict[str, Tuple[int, bytes]]) -> Tuple[bytes, Tree]:
        """Create a tree object from a dictionary of entries"""
        tree = Tree()
        for name, (mode, blob_id) in entries.items():
            tree.add(name.encode("utf-8"), mode, blob_id)
        self.repo.object_store.add_object(tree)
        return tree.id, tree

    def commit(
        self, state: GameState, message: str, policy: Optional[str] = None
    ) -> str:
        """Create a commit with the given state and message"""
        # Create blobs for state and policy
        state_id, state_blob = self._make_blob(state.to_raw())

        # Create tree entries
        entries = {"gamestate.json": (0o100644, state_id)}

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
        commit.message = message.encode("utf-8")

        # Add parent if exists
        try:
            refs_dict = self.repo.refs.as_dict()
            if self.branch in refs_dict:
                commit.parents = [refs_dict[self.branch]]
        except Exception as e:
            # No parent, this is the first commit
            print(
                f"No parent commit found (this may be normal for first commit): {str(e)}"
            )
            pass

        # Add the commit object to the object store
        self.repo.object_store.add_object(commit)

        # Update HEAD and branch reference properly
        commit_id = commit.id.decode("utf-8")

        # Update the refs - use set_if_equals for safety
        old_ref = None
        try:
            if self.branch in self.repo.refs:
                old_ref = self.repo.refs[self.branch]
        except Exception:
            pass

        # Update ref with proper atomic operation if possible
        self.repo.refs.set_if_equals(self.branch, old_ref, commit.id)

        # Update our internal tracking to match refs state
        self.branches[self.current_branch] = commit_id

        # Add to undo stack
        self.undo_stack.append(commit_id)

        # Make sure refs are stored to disk
        try:
            self.repo.refs.pack_refs()
        except Exception as e:
            print(f"Warning: Could not pack refs: {str(e)}")

        return commit_id

    def _save_state_to_disk(self, commit_id: str):
        """Save the current repository state to disk"""
        # No need to call do_commit here - that creates a new commit
        # Objects are already persisted by the object_store.add_object operations
        # and refs are persisted by pack_refs()
        pass

    def tag_commit(self, name: str, commit_id: Optional[str] = None) -> str:
        """Create a named tag for a commit (default: current HEAD)"""
        if commit_id is None:
            try:
                refs_dict = self.repo.refs.as_dict()
                if self.branch in refs_dict:
                    commit_id = refs_dict[self.branch].decode("utf-8")
                else:
                    raise ValueError("No current HEAD to tag")
            except Exception as e:
                raise ValueError(f"Error getting current HEAD: {str(e)}")

        # Update internal tags dictionary for our tracking
        self.tags[name] = commit_id

        # Create a Git tag reference properly
        tag_ref = f"refs/tags/{name}".encode("utf-8")
        commit_id_bytes = commit_id.encode("utf-8")

        # Use atomic operation to set the tag
        self.repo.refs.add_if_new(tag_ref, commit_id_bytes)

        # Ensure refs are persisted to disk
        try:
            self.repo.refs.pack_refs()
        except Exception as e:
            print(f"Warning: Could not pack refs for tag: {str(e)}")

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
        refs_dict = self.repo.refs.as_dict()

        # Check if it's a tag
        if ref in self.tags:
            ref = self.tags[ref]
            tag_ref = f"refs/tags/{ref}".encode("utf-8")
            if tag_ref in refs_dict:
                commit_id = refs_dict[tag_ref]
            else:
                # Fall back to our tracked tag
                commit_id = ref.encode("utf-8") if isinstance(ref, str) else ref

        # Handle branch name
        elif ref in self.branches:
            self.current_branch = ref
            self.branch = f"refs/heads/{ref}".encode("utf-8")
            if self.branch in refs_dict:
                commit_id = refs_dict[self.branch]
            else:
                print(f"Warning: Branch {ref} not found in refs")
                return None
        else:
            # Handle commit ID directly
            commit_id = ref.encode("utf-8") if isinstance(ref, str) else ref
            # This is a detached HEAD state
            self.current_branch = None

        # Update HEAD reference properly using symbolic ref API for branches
        try:
            if self.current_branch:
                # Symbolic ref for branch
                self.repo.refs.set_symbolic_ref(b"HEAD", self.branch)
            else:
                # Direct ref for detached HEAD
                self.repo.refs[b"HEAD"] = commit_id

            # Make sure refs are written to disk
            self.repo.refs.pack_refs()
        except Exception as e:
            print(f"Warning: Error updating HEAD reference: {str(e)}")

        # Return the commit ID as string for consistency
        return commit_id.decode("utf-8") if isinstance(commit_id, bytes) else commit_id

    def apply_to_instance(self, commit_id: Optional[str] = None) -> bool:
        """Apply a specific commit to the game instance"""
        if commit_id is None:
            # Use current HEAD properly
            try:
                # Get HEAD properly, following symrefs if needed
                refs_dict = self.repo.refs.as_dict()
                head_value = refs_dict.get(b"HEAD")

                # If HEAD is a symbolic ref, follow it
                if head_value and head_value.startswith(b"ref: "):
                    ref_name = head_value[5:]
                    if ref_name in refs_dict:
                        commit_id = refs_dict[ref_name]
                    else:
                        raise ValueError(
                            f"Symbolic ref {ref_name.decode('utf-8')} not found"
                        )
                else:
                    commit_id = head_value

                if not commit_id:
                    raise ValueError("No current commit to apply")
            except Exception as e:
                raise ValueError(f"Error getting current HEAD: {str(e)}")
        else:
            commit_id = (
                commit_id.encode("utf-8") if isinstance(commit_id, str) else commit_id
            )

        try:
            # Get the commit - ensure it's loaded from disk if needed
            try:
                commit = self.repo.object_store[commit_id]
            except KeyError:
                # Try to load the commit from the on-disk repository
                self.repo.object_store.add_objects_from_pack(commit_id)
                commit = self.repo.object_store[commit_id]

            # Get the tree
            tree = self.repo.object_store[commit.tree]

            # Get the state blob
            if b"gamestate.json" in tree:
                state_id = tree[b"gamestate.json"][1]
                state_blob = self.repo.object_store[state_id]
                state_json = state_blob.data.decode("utf-8")

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
        commit_id_bytes = prev_commit_id.encode("utf-8")

        try:
            # Get the old ref to use with atomic operation
            old_ref = None
            if self.branch in self.repo.refs:
                old_ref = self.repo.refs[self.branch]

            # Update refs with proper atomic operation
            self.repo.refs.set_if_equals(self.branch, old_ref, commit_id_bytes)

            # Update branch tracking
            if self.current_branch:
                self.branches[self.current_branch] = prev_commit_id

            # Update HEAD reference properly
            if self.current_branch:
                # Use symbolic ref for branch
                self.repo.refs.set_symbolic_ref(b"HEAD", self.branch)
            else:
                # Direct ref for detached HEAD
                self.repo.refs[b"HEAD"] = commit_id_bytes

            # Make sure refs are written to disk
            self.repo.refs.pack_refs()

        except Exception as e:
            print(f"Warning: Error updating references during undo: {str(e)}")

        return prev_commit_id

    def get_policy(self, commit_id: str) -> Optional[str]:
        """Get the policy associated with a commit"""
        commit_id = (
            commit_id.encode("utf-8") if isinstance(commit_id, str) else commit_id
        )

        try:
            try:
                commit = self.repo.object_store[commit_id]
            except KeyError:
                # Try to load from disk if needed
                self.repo.do_pack()
                commit = self.repo.object_store[commit_id]

            try:
                tree = self.repo.object_store[commit.tree]
            except KeyError:
                # Try to load tree from disk
                self.repo.do_pack()
                tree = self.repo.object_store[commit.tree]

            if b"policy.py" in tree:
                policy_id = tree[b"policy.py"][1]
                try:
                    policy_blob = self.repo.object_store[policy_id]
                except KeyError:
                    # Try to load blob from disk
                    self.repo.do_pack()
                    policy_blob = self.repo.object_store[policy_id]

                return policy_blob.data.decode("utf-8")
        except KeyError:
            pass
        except Exception as e:
            print(f"Error getting policy: {str(e)}")

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
                    try:
                        commit = self.repo.object_store[commit_id]
                    except KeyError:
                        # Try to load from disk if needed
                        self.repo.do_pack()
                        commit = self.repo.object_store[commit_id]

                    history.append(
                        {
                            "id": commit_id.decode("utf-8")
                            if isinstance(commit_id, bytes)
                            else commit_id,
                            "message": commit.message.decode("utf-8"),
                            "timestamp": commit.commit_time,
                            "has_policy": self._has_policy(commit.tree),
                        }
                    )

                    if commit.parents:
                        commit_id = commit.parents[0]
                    else:
                        break
                except KeyError:
                    # Can't find the commit, maybe it's not loaded
                    break
                except Exception as e:
                    print(f"Error processing commit {commit_id}: {str(e)}")
                    break
        except Exception as e:
            print(f"Error getting history: {str(e)}")

        return history

    def _has_policy(self, tree_id):
        """Check if a tree contains a policy file"""
        try:
            try:
                tree = self.repo.object_store[tree_id]
            except KeyError:
                # Try to load from disk if needed
                self.repo.do_pack()
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
                return {
                    "status": "no_policies",
                    "message": "Neither commit has a policy",
                }

            if policy1 is None:
                return {
                    "status": "added",
                    "message": "Policy added in second commit",
                    "policy": policy2,
                }

            if policy2 is None:
                return {
                    "status": "removed",
                    "message": "Policy removed in second commit",
                    "policy": policy1,
                }

            # Both commits have policies, compute line-based diff
            import difflib

            diff = list(
                difflib.unified_diff(
                    policy1.splitlines(keepends=True),
                    policy2.splitlines(keepends=True),
                    fromfile=f"policy-{commit_id1[:8]}.py",
                    tofile=f"policy-{commit_id2[:8]}.py",
                )
            )

            return {
                "status": "modified",
                "message": "Policy modified between commits",
                "diff": "".join(diff),
                "policy1": policy1,
                "policy2": policy2,
            }
        except Exception as e:
            return {"status": "error", "message": f"Error comparing policies: {str(e)}"}
