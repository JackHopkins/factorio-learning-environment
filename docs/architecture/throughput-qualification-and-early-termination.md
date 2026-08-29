# Throughput qualification and early epoch termination

## Implemented autonomous detector and audit

The local envd runtime can reserve Factorio workers exclusively for throughput
audits with `--audit-rcon-ports`. These workers are never leased to policies.
For a sustained order, every completed intervention whose tools could have
changed the factory marks the cheap detector dirty. At the intervention
boundary envd queries the target products through the privileged
`get_recent_rate` FLE action, backed by `LuaFlowStatistics.get_flow_count`.
Timestamped direct-harvest and hand-craft events are subtracted before the
rate is compared with the hidden trigger ratio.

Only a detector hit serializes `GameState`. The source world remains paused
while an audit worker restores the state, re-adopts the physical customer
depots, discards a burn-in interval, and runs a deterministic-random holdout
whose duration is an integer number of hidden subwindows. Every product must
meet both the average target and the configured minimum subwindow fraction.
Adaptive customer orders additionally require the same average and subwindow
conditions at the autonomous depot boundary. Producing an item without
servicing the customer therefore cannot end the epoch.

A passing audit certifies the sustained order and returns
`terminal_reason=throughput_audit_passed` from the intervention that exposed
the candidate. The harness ends the epoch immediately. A failed audit is
privileged evidence only: the live state is unchanged and rollout continues.
The successful result is cached and reused by authoritative finalization, so
the live world is not subjected to a second holdout.

The current termination granularity is one submitted program, rather than an
individual FLE call within that program. Post-tool hooks only dirty the cheap
detector because cloning and reserving another worker from inside a synchronous
tool callback would introduce re-entrant service locks. This still terminates
before another model turn and preserves atomic program semantics.

Status: design note after the first autonomous-throughput implementation,
2026-08-28.

## Current decision

Keep two measurements separate:

1. The continuous contract score measures delivery across the committed order
   window and remains the rating/training signal.
2. An autonomous qualification freezes agent actions, advances the simulation,
   and measures exact customer-depot throughput over a server-selected window.

`factorio_check_throughput` is a diagnostic student tool. It consumes simulation
time, returns exact per-product rates, and does not directly grant reward. The
runner also performs one authoritative qualification at the end of every
sustained order. A capability becomes autonomous only when both the continuous
score and the authoritative qualification score are at least `0.60`.

The server chooses the check duration. It targets at least two expected units
per order line and clamps the window to one-to-five simulated minutes. The
student cannot select a conveniently short measurement window.

## Training profiles

Disable `factorio_check_throughput` in the normal RL training tool profile. The
authoritative verifier-side qualification remains enabled. Tool availability
must be included in the participant/harness identity so runs with and without
diagnostic feedback are never pooled into one rating series.

For OPD/OPSD or teacher-driven data generation, the diagnostic tool may be
enabled deliberately. Its outputs can provide useful correction targets and
make throughput failures legible, but trajectories must be tagged as
probe-assisted. They should not be treated as equivalent to unassisted policy
rollouts.

Exact diagnostic feedback is not itself reward hacking. It becomes a reward
hacking channel if invoking a probe directly raises reward, selects an easier
task, resets a deadline, or grants an autonomous certificate. None of those
effects should occur.

## Why an epoch cannot simply end when quantity is delivered

A one-shot order can finish immediately when every line is delivered. A
sustained order makes a claim about behavior over time. Total delivered volume
does not prove sustained service because a manually stocked buffer can create a
large terminal burst.

Waiting for every deadline is nevertheless wasteful once an autonomous factory
has clearly demonstrated the committed rate. We need an early-success protocol,
not merely a shorter fixed deadline.

## Proposed early-success protocol

Add a student action tentatively named `submit_throughput_ready` with these
semantics:

1. Submission is valid only for an open sustained order.
2. The environment records the pre-submission state and freezes agent actions.
3. The server runs the canonical qualification window; the student cannot set
   its duration, phase, products, or thresholds.
4. Qualification uses customer-depot traffic and returns exact line rates and
   scores.
5. If qualification passes and continuous service to date also meets the
   threshold, the order ends early as fulfilled.
6. If qualification fails, the elapsed qualification time is charged to the
   deadline and control returns to the agent if time remains.
7. A failed submission never abandons the order, changes its difficulty, or
   suppresses the eventual authoritative deadline result.

This makes early termination a success-only optimization. A policy cannot use
submission to escape a hard example. Repeated probes are naturally limited by
the deadline, but a minimum cooldown or maximum diagnostic count may still be
useful for inference cost and trace clarity. Such a limit is a tool-use policy,
not an intervention budget for normal factory work.

## Automatic early qualification

The environment may initiate the same check without student submission when
all of the following are true:

- continuous line scores are already above the qualification threshold;
- recent depot delivery covers every requested product;
- sufficient time has elapsed to make the test statistically meaningful;
- no qualification is already running;
- the remaining deadline exceeds the canonical check window.

Automatic checks should be conservative. Triggering them too often inserts
unproductive simulation gaps and can distort factory dynamics. The initial
implementation should support explicit submission plus the final authoritative
check before adding an automatic midpoint trigger.

## Reward-hacking and validity risks

### Preloaded buffers

The largest unresolved weakness is that a player can manually stock a source
chest before qualification and let an inserter drain it during the frozen
window. This proves unattended delivery for the window, but not closed-loop
mining and production. The current combination of continuous scoring plus an
autonomous check reduces this exploit but does not eliminate it.

Long-run options include:

- qualification windows long enough to exceed plausible buffer coverage;
- auditing recent agent insertions into machines and staging inventories;
- item-flow provenance from extraction through processing to the depot;
- requiring sustainable prerequisite certificates for the production chain;
- randomized or repeated hidden qualification windows;
- controlled buffer normalization before a robustness check.

Provenance is the strongest answer but the most invasive. Longer randomized
windows plus capability-chain closure are the likely practical intermediate
design.

### Probe timing and cherry-picking

The student may submit immediately after observing a favorable production
phase. Server-selected duration helps, but deterministic phase-sensitive
windows can still be selected. Hidden jitter or an anytime-valid sequential
test can reduce this without obscuring the reported throughput.

### Failure as an escape action

Never terminate an order merely because a submitted qualification failed.
Otherwise training can learn to submit immediately on hard tasks to shorten
negative trajectories or manipulate task sampling.

### Reward timing

Early success must not silently change the main contract reward. Continuous
performance should remain normalized against the committed demand and window.
Any reward for time efficiency must be a separate, bounded channel so it cannot
outweigh throughput or automation quality.

### Information leakage

Diagnostic results may expose exact verifier measurements. This is acceptable
for tool-assisted evaluation and OPD/OPSD data generation, but normal training
should disable the tool and rely on ordinary factory observations. The hidden
authoritative result remains in the trace for learning and audit.

## Implementation sequence

1. Keep the current end-of-order authoritative qualification and continuous
   rating score.
2. Add a training tool profile that excludes `factorio_check_throughput` while
   retaining verifier-side qualification.
3. Implement `submit_throughput_ready` as a non-terminal failure / terminal
   success transition.
4. Persist every qualification request, window, exact result, and state digest.
5. Evaluate buffer exploitation before using autonomous certificates as a
   direct RL reward.
6. Only then consider automatic midpoint or sequential early qualification.

## Operational lesson from the first restarted run

The first run using this design did not reach Factorio. OpenCode Go returned
thirteen consecutive `429 FreeUsageLimitError` responses. During provider
backoff, envd's lease expired because the runner heartbeat updated only its
local heartbeat file. The runner now renews the environment lease independently
of provider progress. Provider throttling must remain an infrastructure outcome
and must never destroy or rate the active factory state as a model failure.
