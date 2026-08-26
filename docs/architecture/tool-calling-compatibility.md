# Tool-calling compatibility contract

Status: implemented transport contract, 2026-08-26

This note defines what a modern model harness can rely on when it connects to
Factorio envd. It deliberately separates direct MCP calls, programmatic action
composition, and provider-specific programmatic tool-calling features.

## Direct MCP calls

The lease-bound MCP adapter exposes two direct tools:

- `factorio_observe_factory` reads the current public observation.
- `factorio_execute_program` submits one Python program as one environment
  intervention.

The adapter uses newline-delimited JSON-RPC with request IDs and negotiates MCP
protocol revisions from `2024-11-05` through `2025-11-25`. Its stdio dispatcher
handles one input line at a time, so one adapter process is a serialized queue.
A client may still pipeline requests and correlate responses by ID, but this
adapter does not provide intra-process parallel execution.
Use separate MCP sessions and leases for genuinely independent rollouts.

The HTTP service underneath the adapter is safe to call concurrently. Requests
for different leases can run in parallel subject to worker capacity. Requests
for the same lease are protected by the lease lock (a `threading.RLock` in the
local backend and an `asyncio.Lock` in the AgentENV gateway). Execution,
observation, finalization, pause/resume, and release therefore do not overlap
on one world. The server assigns `event.sequence` while holding that lock;
clients must use that value rather than infer order from response timing.

MCP has no standard capability bit that means "parallel tool calls supported."
The envd health capability manifest therefore reports the more precise
semantics:

| Feature | Value | Meaning |
| --- | --- | --- |
| `concurrent_request_safe` | `true` | The service can receive concurrent HTTP requests. |
| `per_lease_serial_execution` | `true` | One lease's operations are serialized. |
| `parallel_world_mutations` | `false` | A single Factorio world is never mutated concurrently. |

## Programmatic action composition

The Python submitted to `factorio_execute_program` is the environment's
programmatic composition interface. A program can call public FLE names in
sequence and use loops and conditionals to keep dependent work in one
round-trip. The action profile validates the whole program before execution;
the resulting sequence of FLE calls is recorded as one `ActionEvent`, with the
executed tool names retained for auditing. Calls are synchronous and source
ordered. The program cannot make network/MCP calls or access host files.

This is distinct from provider-native PTC or code-mode protocols. OpenAI,
Anthropic, OpenCode, and other harnesses may have their own mechanisms for
letting a model compose tool calls, but envd does not claim to implement those
provider protocols. They must either submit ordinary code through
`factorio_execute_program` or dispatch the two direct MCP tools themselves.
The manifest advertises `programmatic_action_composition=true` and
`provider_native_programmatic_tool_calling=false` to make that boundary
explicit.

## Harness obligations

When a model response contains multiple direct tool calls, a harness may
dispatch them concurrently only when it is prepared for per-lease
serialization. It must preserve each JSON-RPC/tool-call ID, surface
`isError=true` for failed MCP calls, and retain each returned event sequence.
It must not treat parallel submission as permission to mutate one lease in
parallel. A retry after a transport timeout can repeat a mutation; callers
must reuse the same `request_id` for the same logical execute call. Envd caches
the program hash and exact `ExecutionResult` for the lease lifetime. An
identical replay returns that result without advancing the world, consuming an
intervention, or allocating another event sequence. Reusing the key for a
different program returns HTTP 409. The bundled HTTP and MCP clients make one
automatic keyed retry after an ambiguous transport failure; returned HTTP
errors and unkeyed mutations are never retried automatically.

MCP results are bounded as complete JSON documents. If the serialized envd
payload exceeds the adapter limit, both text and `structuredContent` contain a
truncation envelope with `original_json_chars`, `original_json_sha256`, and a
`json_prefix`. The adapter never cuts serialized JSON mid-token.

## RLVR follow-up

The repeated-identical-failure circuit breaker is currently an evaluation
harness protection against wasting a run. It is not a training-loop policy and
must not be copied into RLVR without analysis. **TODO: brainstorm the
three-consecutive-failures behavior for actual training**, including reward and
credit-assignment consequences, whether blocked attempts are observable to the
policy, downstream effects on exploration and recovery, and possible reward
hacking through harmless-looking program variants or deliberate failure loops.
