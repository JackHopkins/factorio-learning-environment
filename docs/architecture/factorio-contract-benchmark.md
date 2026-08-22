# Factorio contract benchmark substrate

Status: implemented vertical slice, 2026-08-22

## Decision

Move scoring outside the factory. The legacy throughput tasks score internal
production statistics; this substrate adds an externally-owned demand side so
that reward comes only from items physically crossing into customer-owned
sinks. Internal production counts, inventory shuffles, and crafting milestones
generate no fulfillment credit by construction.

Four subsystems hang off the same worker sync loop:

| Subsystem | Module | Purpose |
|---|---|---|
| Customer contracts | `fle/envd/customer.py` | hidden demand schedules, sink-based fulfillment, signed receipts |
| World disruptions | `fle/envd/perturbations.py` | hidden shock schedule, per-network recovery measurement |
| Blueprint library | `fle/envd/blueprints.py` | generation-scoped reusable factory fragments |
| Map lifecycle | `fle/envd/lifecycle.py` | rollout-source quotas, recoverability retirement |

All four are sealed behind the `factorio-envd` lease API described in
[the RLVR stack boundary](factorio-rlvr-stack.md). Nothing here changes the
legacy Gym/REPL path; native specs opt in per field.

## Customer contracts

### Hidden schedules as immutable input

A `CustomerContractSpec` ships inside `FactorioTaskSpec` and is therefore
covered by the spec fingerprint. The full order stream exists before the
episode starts -- the benchmark equivalent of hidden unit tests -- while the
acting policy only ever observes orders whose issue tick has passed:

- `Observation.contracts` exposes `OpenContractView` records only;
- weights, penalties, thresholds, and future orders are deliberately absent
  from the student projection (`ContractEngine.student_view`);
- schedule identity is committed via a SHA-256 `commitment` over the sorted,
  canonical order list.

Schedules are generated deterministically by
`generate_contract_schedule(ScheduleConfig, seed)` over a curated product
catalog with tier and reference-throughput metadata. Same inputs produce
byte-identical schedules on any platform; calibration against measured
capability belongs to the curriculum layer, not the generator.

### Sink-based fulfillment measurement

Depots are vanilla steel chests placed near spawn by an admin-only Lua tool
(`fle/env/tools/admin/customer_depot`). Their properties are hardened:
`destructible=false`, `operable=false`, mining disabled where the runtime
allows it. A pcall-guarded `script.on_nth_tick(6)` drain loop counts chest
contents into 60-tick delivery buckets and immediately destroys the items.
Credited deliveries can therefore never be extracted back out; stealing from
a depot before a drain cycle simply forfeits the units. Destroyed or mined
depots are recorded as tamper events and rebuilt at their original positions.
Customer depots are excluded from perturbation blast radii.

Attribution walks delivery buckets chronologically and credits units to the
earliest open order needing that product (FIFO by issue tick). Deliveries
before any compatible open order are recorded as `unattributed`. Buckets are
credited at their end tick, which can under-credit by at most one bucket but
never grants credit before physical delivery.

### Reward integral

Per order ``j``: ``r_j = min(1, accepted/requested)`` weighted by order weight;
``R = sum(w_j r_j) / sum(w_j) - lambda * sum(w_j max(0, 1 - r_j)) / sum(w_j)``.

One-shot orders accept deliveries up to ``due_tick + grace_ticks``. Sustained
orders slice their window at 3600-tick granularity and average per-slice
scores, so steady supply beats burst-and-idle: a burst fills one slice and
starves the rest. Never-revealed orders contribute nothing to the integral --
demand the customer has not yet issued cannot dilute fulfillment.

Never-revealed demand also cannot leak: reveal transitions emit
`contract_issued` verifier events, completion emits `contract_fulfilled`,
and deadline misses emit `contract_expired`.

### Receipts

Final evaluation produces an HMAC-SHA256 receipt over the canonical result
payload (commitment, per-order outcomes, aggregate ratio, unattributed
totals, finalized tick, lease context). The key comes from
`FLE_CUSTOMER_RECEIPT_KEY`; unset keys fall back to an ephemeral session
secret, which keeps local runs honest but only verifiable within the process.
Benchmark deployments must pin the environment variable. Receipt MAC and
commitment land in snapshot `evidence` and `metrics["customer_receipt"]`, so
published trajectories can be re-verified without trusting the envd process.

## World disruptions

`DisruptionScheduleSpec` hides a shock stream behind the same pattern: the
schedule is immutable benchmark input, the blast radius is whatever exists.
Three primitives cover the standard failure taxonomy:

| Kind | Lua command | Covers |
|---|---|---|
| `resource_depletion` | `deplete_area` | ore patch exhausted |
| `entity_destruction` | `destroy_entities` | power loss, severed belts, removed modules, rail cuts |
| `enemy_wave` | `spawn_enemies` | biter pressure |

Entity targeting resolves against the factory centroid (with character
fallback) and excludes characters and customer depots. Before destruction,
each victim's recipe products are captured into the event payload as
`affected_products` -- the recovery metric's measurement target.

### No-op discipline

Application requires an observable effect. A shock whose result shows zero
destroyed/spawned entities is recorded as `status="no_op"` rather than
`applied`: a schedule cannot bank credit against missing targets. Failures
degrade to failed records instead of raising -- injected handlers are wrapped
so telemetry bugs never kill the simulation (an unhandled scenario-event
error terminates the running game).

### Recovery measurement

For every applied throughput-affecting shock the engine estimates per-product
baseline output rates from production-statistic intervals fully before the
shock, then measures ``T_recovery = t(return) - t(applied)`` where return
requires every tracked product to individually reach
``recovery_rate_threshold x baseline`` after ``recovery_min_ticks``. Tracking
is gated on the affected product networks derived from destroyed machines'
recipes; pure logistics damage falls back to the largest pre-shock products.
Per-product gating means flooding cheap decoy items cannot register a dead
line as restored. Counterfactual branch probes can later replace the
heuristic baseline estimate through `StateQualitySnapshot.future_probes`.

## Blueprint library

Blueprints are learned artifacts with explicit ownership semantics:

- `blueprint_scope=None` (benchmark default): ephemeral per-lease memory.
  Evaluation never sees cross-episode state.
- `blueprint_scope=<lineage>`: durable SQLite store (WAL) shared by every
  rollout in a training generation; fresh generations start clean.

Agents get four commands (`fle/env/tools/agent/blueprint`): `save`
(bounded-area capture, characters excluded), `place` (by library name or
inline exchange string), `list`, `get`. Content stays server-side; the
observation carries summaries only (`Observation.blueprints`), which pushes
the policy toward referencing structural patterns instead of re-emitting
strings.

Placement economics close the infinite-infrastructure exploit:

1. the full material bill is aggregated from ghost types plus module/fuel
   requests *before* anything is placed;
2. placement is all-or-nothing -- missing materials return
   `missing_materials` with deficits and leave the world untouched;
3. success debits the items from character inventory and charges
   construction time (15 ticks/entity) against the task clock.

Unlike the admin loader, agent placement does not call
`research_all_technologies()`; one blueprint must not unlock the tech tree.
Usage counters feed trainer-side decay policies (`prune(min_times_placed,
keep_newest)`, `drop_scope`); the store itself never decides fitness.

## Map lifecycle

`GenerationManager` implements the generation-level rollout policy: weight
updates are decoupled from map resets. One frozen policy plays out a
generation composed of

- **fresh** seeds (default 55%): every generation re-demonstrates bootstrap;
- **inherited** continuations (25%): resume the healthiest active lineage
  from its latest checkpoint;
- **pathological** states (20%): continue the weakest lineage with two
  tick-0 shocks injected through the disruption engine, forcing genuine
  recovery practice.

Source sampling uses largest-remainder counting, so a block of N episodes
matches the configured fractions exactly.

Retirement follows ``V_continue(s) < V_restart - C_reset``. ``V_restart``
is the running mean of first-episode value across fresh lineages in the
generation -- the policy's own measured bootstrap capability -- so a policy
that optimizes mature factories while regressing at early game raises its
own bar. When counterfactual probes exist in the snapshot they override the
heuristic continuation estimate outright. Outcomes classify as `healthy`,
`degraded_recoverable` (deliberately continued under the pathological quota),
`dominated` (retired, checkpoints retained for hindsight extraction), or
`horizon_reached` (tick/episode caps force rotation regardless of health).

`CheckpointPool` persists serialized `GameState` blobs per lineage under
`FLE_LIFECYCLE_DIR`. Workers restore them through
`checkpoint_id="lifecycle:<lineage>:ep<N>"` with `reset_position=False`;
continuation episodes resume in place.

## Clock discipline

Two clocks exist and must not be conflated:

- **Episode simulation time** (`game.tick - epoch`): advances whenever the
  game is unpaused. Contract deadlines, bucket attribution, disruption
  triggers, and recovery windows all run on this clock. The epoch is pinned
  Lua-side at depot placement and Python-side at task start.
- **Action-cost ticks** (`storage.elapsed_ticks`): FLE's virtual accounting
  of movement/crafting/mining time, reset per episode. Used for intervention
  bookkeeping, not for scheduling.

`sleep(n)` adds n seconds of virtual action ticks and waits the corresponding
real time while unpaused, so real simulation time advances during sleeps,
holdout windows, and verification -- not during model latency, which is spent
paused by design.

## Wire surface

Additive fields on `FactorioTaskSpec` (all fingerprint-covered):
`customer`, `perturbations`, `blueprint_scope`, `lineage_id`,
`generation_id`. Additive observation fields: `contracts`, `blueprints`.
New verifier event kinds: `contract_issued`, `contract_progress`,
`contract_fulfilled`, `contract_expired`; existing kinds reused for
`perturbation_applied` and `recovery_completed`. New reward channels:
`contracts`, `contract_penalty`.

Sealing properties, unchanged from the RLVR boundary: generated programs
cannot reach underscore-prefixed admin tools (`_customer_depot`,
`_perturbation`) because the fle-program-v1 guard rejects private names;
future orders are unreachable through any student-facing channel; benchmark
internals ship only inside signed summaries.

## Testing

Unit suites run without Factorio (`no_factorio` marker):
`tests/envd/test_customer.py`, `test_perturbations.py`,
`test_blueprints.py`, `test_lifecycle.py`, `test_game_state_restore.py`.
Live suites require a container on `localhost:27000`:
`test_customer_live.py` (delivery-to-receipt end to end),
`test_perturbations_live.py` (pre- and post-intervention shocks),
`test_blueprints_live.py` (cross-lease save/place round trip).

Known live-environment caveats: scenario structures survive resets near
spawn, so tests scan for contiguous free ground; empty Lua tables round-trip
as Python dicts; exchange strings must be quote-wrapped Lua-side to survive
the RCON dump parser.

## Evidence plane

RolloutPlane consumes this substrate out of band: one envd lease maps to one
bundle-pinned rollout lease, finalizer snapshots become reward/termination
events through `EnvironmentRecorder`, and customer receipts plus schedule/
disruption commitments travel as artifact references. RolloutPlane Viz reads
the same ledger for run comparison. See
[RolloutPlane integration notes](https://github.com/HumanDotPy/RolloutPlane/blob/main/docs/integrations.md).
