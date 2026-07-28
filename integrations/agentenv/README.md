# AgentENV production runtime

AgentENV is the preferred runtime for Ubuntu training clusters. Windows and
ordinary local development continue to use the Docker/FLE pool. Both expose the
same public `factorio-envd` contract, so Verifiers v1, benchmark clients, and
Prime-RL do not select infrastructure directly.

```text
Windows development
  public factorio-envd -> fixed Docker/RCON worker pool

Ubuntu training
  public factorio-envd -> AgentENV gateway
                         -> one Firecracker sandbox per lease
                         -> Factorio + inner factorio-envd
```

AgentENV owns process isolation, elastic sandbox lifecycle, pause/resume,
memory-and-filesystem snapshots, and live forks. The inner service remains
authoritative for Factorio actions, observations, task provisioning, rewards,
and verifier evidence.

## Prerequisites

- Ubuntu 24.04 and Linux kernel 6.8 or newer.
- `/dev/kvm` available to the AgentENV runtime.
- Privileged AgentENV runtime pods when using Kubernetes.
- A private OCI registry available to the AgentENV nodes.
- AgentENV installed from <https://github.com/kvcache-ai/AgentENV>.

The currently reviewed upstream revision and OpenAPI hash are recorded in
`compatibility.toml`. AgentENV is moving quickly; use that revision for the
first cluster deployment or repeat the contract audit and update the lock
before using a newer revision.

Do not publish built Factorio images to a public registry without confirming
redistribution permission. This repository contains only a build recipe; the
recipe references the upstream headless image.

## Build the guest image

From the repository root:

```bash
docker build \
  -f integrations/agentenv/Dockerfile \
  -t YOUR_PRIVATE_REGISTRY/waslab/factorio-envd:0.3.0 \
  .
docker push YOUR_PRIVATE_REGISTRY/waslab/factorio-envd:0.3.0
```

Configure AgentENV with credentials for that registry, then import the image as
a template:

```bash
aenv pull \
  YOUR_PRIVATE_REGISTRY/waslab/factorio-envd:0.3.0 \
  --name waslab-factorio-envd-0.3.0 \
  --start-cmd /usr/local/bin/factorio-agentenv-entrypoint \
  --probe 8172 \
  --timeout 1200
aenv template list --output json
```

The explicit start command is required. At the reviewed AgentENV revision,
`aenv pull` does not derive `startCmd` from the OCI image's `ENTRYPOINT`.
The readiness probe prevents a template from being published until both the
Factorio process and the inner `factorio-envd` service are operational.

Record the immutable template UUID. Do not use a mutable image tag as the
experiment identifier.

## Start the public gateway

```bash
export AENV_API_URL=http://agentenv-gateway.agentenv-system.svc:8000
export AENV_API_KEY=YOUR_SINGLE_TENANT_KEY
export AENV_TEMPLATE_ID=THE_TEMPLATE_UUID
export AENV_FACTORIO_CAPACITY=64
export AENV_SANDBOX_TIMEOUT=1800

fle-envd \
  --runtime agentenv \
  --host 0.0.0.0 \
  --port 8172 \
  --lease-ttl 86400
```

`--runtime auto` selects AgentENV whenever `AENV_TEMPLATE_ID` is set and uses
the local Docker/RCON runtime otherwise.

`AENV_SANDBOX_TIMEOUT` is the idle interval before AgentENV auto-pauses the
microVM. `--lease-ttl` is the longer logical rollout lifetime. Each successful
observation, intervention, or verification refreshes both clocks.

Only the public gateway should be reachable by Verifiers or Prime-RL. Factorio
RCON stays private inside each sandbox. The gateway reaches the inner envd
through AgentENV's HTTP reverse proxy.

Do not expose the AgentENV control plane directly to the public internet.
Place the public `factorio-envd` gateway and AgentENV on a private cluster
network, use a non-default API key, and allow only the gateway to reach the
AgentENV API.

## Verify snapshot and fork semantics

```bash
python integrations/agentenv/smoke.py \
  --envd-url http://127.0.0.1:8172
```

The smoke test creates one lease, forks two live children, verifies identical
initial state hashes, confirms that intervention histories do not leak between
children, creates a durable checkpoint, and releases every sandbox.

Before a paid training run, repeat this test under concurrency and record:

- sandbox creation and guest-health latency;
- fork latency for 2, 4, 8, and 16 children;
- RSS and snapshot-storage growth;
- failure and cleanup rates over at least 100 fork cycles;
- large-factory tick throughput relative to the Docker backend.

Native Factorio saves remain the portable source of benchmark initial states.
AgentENV memory snapshots are an acceleration and branching mechanism, not the
only durable representation of a task.
