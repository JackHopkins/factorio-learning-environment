"""Create a detached, compatibility-pinned Prime-RL checkout.

The script is intentionally conservative: it creates a new directory or verifies an
existing checkout. It never updates or rewrites an existing Prime-RL worktree.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPATIBILITY = HERE / "compatibility.toml"


def run(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=None,
    )
    return completed.stdout.strip()


def revision(path: Path) -> str:
    return run("git", "rev-parse", "HEAD", cwd=path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify the Prime-RL checkout pinned for this FLE fork."
    )
    parser.add_argument("target", type=Path, help="New or existing Prime-RL directory")
    args = parser.parse_args()

    with COMPATIBILITY.open("rb") as handle:
        pins = tomllib.load(handle)
    prime = pins["prime_rl"]
    verifiers = pins["verifiers"]
    target = args.target.expanduser().resolve()

    if target.exists():
        if not (target / ".git").exists():
            parser.error(f"refusing to use non-git directory: {target}")
        if revision(target) != prime["commit"]:
            parser.error(
                f"existing checkout is not pinned to {prime['commit']}; "
                "choose a new target or reconcile it manually"
            )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        run("git", "clone", "--filter=blob:none", prime["repository"], str(target))
        run("git", "checkout", "--detach", prime["commit"], cwd=target)
        run("git", "submodule", "update", "--init", "--recursive", cwd=target)

    verifiers_path = target / "deps" / "verifiers"
    if not verifiers_path.exists():
        parser.error("Prime-RL Verifiers submodule is absent; initialize submodules")
    actual_verifiers = revision(verifiers_path)
    if actual_verifiers != verifiers["commit"]:
        parser.error(
            f"Verifiers pin mismatch: expected {verifiers['commit']}, "
            f"found {actual_verifiers}"
        )

    print(f"Prime-RL:  {revision(target)}")
    print(f"Verifiers: {actual_verifiers}")
    print(f"Checkout:   {target}")
    print("Next: follow integrations/prime/README.md from the FLE checkout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
