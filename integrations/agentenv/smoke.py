"""Exercise live AgentENV forking through the public factorio-envd contract."""

from __future__ import annotations

import argparse
import asyncio

from fle.envd.client import HTTPEnvironmentClient
from fle.envd.microtasks import get_microtask


async def run(base_url: str) -> None:
    async with HTTPEnvironmentClient(base_url, timeout_seconds=300) as client:
        health = await client.health()
        if not health.capabilities.features.get("clone"):
            raise RuntimeError(
                "The selected envd runtime does not advertise live cloning"
            )

        source = await client.lease(get_microtask("micro_place_lab_v1"))
        lease_ids = [source.lease_id]
        try:
            source_observation = await client.observe(source.lease_id)
            forked = await client.fork(source.lease_id, count=2)
            if forked.failures or len(forked.branches) != 2:
                raise RuntimeError(f"AgentENV fork was incomplete: {forked}")
            lease_ids.extend(branch.lease_id for branch in forked.branches)

            branch_observations = [
                await client.observe(branch.lease_id) for branch in forked.branches
            ]
            hashes = {
                source_observation.state_hash,
                *(observation.state_hash for observation in branch_observations),
            }
            if len(hashes) != 1:
                raise RuntimeError(f"Forks did not begin at one state: {hashes}")

            await client.execute(
                forked.branches[0].lease_id,
                "print(inspect_inventory())",
            )
            first = await client.finalize(forked.branches[0].lease_id)
            second = await client.finalize(forked.branches[1].lease_id)
            if len(first.action_events) != 1 or second.action_events:
                raise RuntimeError("Fork event histories leaked between sandboxes")

            checkpoint = await client.checkpoint(
                source.lease_id,
                name="factorio-agentenv-smoke",
            )
            print(
                {
                    "status": "ok",
                    "source_state_hash": source.initial_state_hash,
                    "branch_count": len(forked.branches),
                    "checkpoint_id": checkpoint.checkpoint_id,
                }
            )
        finally:
            for lease_id in reversed(lease_ids):
                try:
                    await client.release(lease_id)
                except Exception:
                    pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    args = parser.parse_args()
    asyncio.run(run(args.envd_url))


if __name__ == "__main__":
    main()
