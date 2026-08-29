# Adaptive contract benchmark implementation specification

Status: implemented development policy (`adaptive-contract-benchmark-0.5.0-dev`)

This document specifies a progression-aware benchmark for persistent Factorio
agents. The benchmark presents a sequence of customer orders inside one
persistent factory, adapts order difficulty to the observed factory state, and
produces reconstructable capability evidence. Factory progress and agent
performance are separate concepts: the former describes what the factory can
reliably do, while the latter describes how efficiently the agent expands or
uses that capability.

TrueSkill supplies the online ability estimate. A calibrated contextual model
supplies contract difficulty. PLR and ACCEL are training policies only; neither
changes the meaning of an official benchmark score.

## 1. Objectives

The system must separately report:

1. Capability on the published contract distribution.
2. Orders and units fulfilled, including progression-stage coverage.
3. Simulation-time and intervention efficiency.
4. Rating uncertainty, extrapolation, and infrastructure failures.

The primary leaderboard value is a conservative TrueSkill score. Orders
fulfilled, stage coverage, simulation ticks, interventions, and efficiency are
first-class companion metrics, not hidden diagnostics.

TrueSkill is an agent-performance metric, not the definition of factory
progress. Capability evidence remains authoritative even when an epoch is
unrated or when the rating model is experimental.

## 2. Hard invariants

1. The factory persists across every epoch in one session.
2. Each epoch has exactly one committed order.
3. The order cannot change after the agent observes it.
4. Difficulty uses the frozen pre-order context, never post-order behavior.
5. Order deadlines use Factorio simulation ticks.
6. Model thinking time does not consume a deadline while simulation is paused.
7. Wall-clock time is diagnostic and a runner fail-safe, not task difficulty.
8. Selection randomness is seeded, recorded, and replayable.
9. Rating, feature, generator, bank, game, and calibration versions accompany
   every result.
10. Official evaluation banks are immutable and isolated from training replay.
11. Every rating can be reconstructed from retained epoch records.
12. Provider-specific harness code cannot alter selection or rating policy.
13. The agent receives a brief operating objective, never hidden benchmark
    policy, grading details, capability-graph internals, or rating logic.

## 3. Terminology

- **Session**: one persistent factory, one agent conversation, multiple epochs.
- **Epoch**: one customer order from commitment through final outcome.
- **Template**: a parameterized order family.
- **Candidate**: a template instantiated against a context and seed.
- **Context**: passive factory measurements captured immediately before an
  epoch.
- **Raw difficulty**: calibrated difficulty before current factory advantages.
- **State advantage**: difficulty reduction from existing technology,
  inventory, infrastructure, and throughput.
- **Effective difficulty**: raw difficulty minus state advantage.
- **Official bank**: versioned templates, private seeds, calibrated ranges, and
  selection policy used for scoring.
- **Training level**: a replayable order/context seed used by PLR or ACCEL.

## 4. Module ownership

| Module | Responsibility |
| --- | --- |
| fle/envd/customer.py | Deterministic active-order state and delivery accounting |
| fle/envd/contract_features.py | Passive snapshots and deterministic feature extraction |
| fle/envd/contract_generator.py | Template expansion, feasibility, quantity, deadlines |
| fle/envd/contract_policy.py | Online product, service-mode, quantity, and deadline policy |
| fle/envd/contract_rating.py | Outcome mapping, contextual difficulty, TrueSkill updates |
| fle/envd/contract_selector.py | Candidate scoring, coverage, seeded selection |
| fle/envd/contract_calibration.py | Offline fitting, validation, manifests |
| fle/envd/contract_curriculum.py | PLR and ACCEL for training only |
| fle/envd/models.py | Backend and runner wire models |
| fle/envd/benchmark_results.py | Epoch records and session summaries |
| scripts/adaptive_contract_benchmark.py | Persistent adaptive evaluation loop |

The runner supports `native`, `hermes`, and `opencode` harness identities.
OpenCode runs in a fresh scratch project with only the lease-bound Factorio MCP
server allowed, automatic context compaction enabled, and one resumable session
across all epochs. The outer runner retains exclusive ownership of lease,
contract, selection, rating, and termination policy. Global OpenCode commands
are convenience entry points only; they do not create orders or grant access to
the host filesystem, shell, web, or delegation tools during an evaluation.

All live harnesses share a short operating objective: operate and expand an
automated factory capable of reliably supplying changing customer demand.
The objective is deliberately qualitative. The model receives the action/API
reference and current order, but not grading criteria, hidden policy, graph
state, rating state, or candidate-selection logic. Tool permissions remain
limited to the supplied Factorio execution and read-only reference interfaces.

Do not put selection, rating, or calibration policy in customer.py. That module
must remain a deterministic order state machine.

## 5. Clock model

Record these clocks independently:

- session_simulation_ticks
- epoch_simulation_ticks
- agent_interventions
- model_seconds
- tool_seconds
- paused_wall_seconds
- runner_wall_seconds

The order deadline is expressed in simulation ticks. The backend owns tick
accounting; the runner owns model, tool, and wall-clock accounting. Never infer
simulation time from wall time and nominal game speed.

The session has no intervention, model-turn, epoch-count, simulation-tick, or
rating-convergence budget by default. Interventions remain measured telemetry.
A 24-hour wall-clock failsafe detects a hung provider, transport, or runner. If
it fires while simulation is paused, mark an infrastructure interruption unless
the agent caused the unresponsive state. Do not record an order loss.

Contract generation is a privileged benchmark operation. It may inspect the
complete current context snapshot, including research, recipes, inventories,
entities, production rates, power, and progression state, so it can issue a
feasible order matched to the actual factory. The agent receives only the
committed current order and public observations; future candidates never leak.

## 6. Normative wire models

The exact syntax may follow the repository's Pydantic version, but these fields
are required:

~~~python
class ContractContextSnapshot(BaseModel):
    schema_version: str
    session_id: str
    epoch_index: int
    captured_tick: int
    technology_ids: tuple[str, ...]
    unlocked_recipe_ids: tuple[str, ...]
    inventory_counts: dict[str, int]
    placed_entity_counts: dict[str, int]
    production_rates_60s: dict[str, float]
    production_rates_300s: dict[str, float]
    power_capacity_kw: float
    power_utilization: float
    logistic_network_count: int
    train_stop_count: int
    pollution_total: float | None
    evolution_factor: float | None
    map_seed_hash: str
    state_digest: str


class ContractDifficultyFeatures(BaseModel):
    schema_version: str
    product_id: str
    product_tier: int
    recipe_depth: int
    missing_technology_count: int
    missing_machine_type_count: int
    required_new_intermediate_count: int
    log_quantity: float
    deadline_ticks: int
    required_rate_per_minute: float
    existing_rate_per_minute: float
    inventory_coverage_ratio: float
    estimated_power_fraction: float
    transport_complexity: float
    stage_band: int


class ContractEpochSpec(BaseModel):
    schema_version: str
    benchmark_version: str
    calibration_version: str
    session_id: str
    epoch_index: int
    template_id: str
    generation_seed: int
    selection_seed: int
    item_name: str
    quantity: int
    deadline_ticks: int
    intervention_budget: None  # reserved wire field; contracts are unbounded
    context: ContractContextSnapshot
    features: ContractDifficultyFeatures
    raw_difficulty: float
    state_advantage: float
    effective_difficulty: float
    commitment_hash: str


class ContractEpochOutcome(BaseModel):
    schema_version: str
    session_id: str
    epoch_index: int
    commitment_hash: str
    status: Literal[
        "fulfilled", "partial", "expired", "abandoned",
        "infrastructure_error", "invalid",
    ]
    delivered_quantity: int
    requested_quantity: int
    completion_ratio: float
    simulation_ticks_used: int
    interventions_used: int
    model_seconds: float
    tool_seconds: float
    runner_wall_seconds: float
    first_delivery_tick: int | None
    completion_tick: int | None
    terminal_state_digest: str


class CapabilityRating(BaseModel):
    model_version: str
    mu: float
    sigma: float
    conservative_score: float
    rated_epoch_count: int
~~~

Serialize mappings and tuples canonically before hashing. Reject unknown schema
or calibration versions instead of applying best-effort defaults.

## 7. Commitments and participant identity

Before showing an order to the agent:

1. Capture the context.
2. Instantiate and select the order.
3. Canonically serialize the complete epoch specification.
4. Compute commitment_hash.
5. Persist the specification.
6. Activate the order.
7. Return the order to the agent.

The outcome repeats the commitment hash. Finalization fails when the hash,
session, or epoch differs.

Participant identity derives from the actual model and harness:

~~~text
participant_id = hash(
    provider
    + model_snapshot
    + harness_version
    + system_prompt_hash
    + tool_manifest_hash
    + inference_settings_hash
)
~~~

Changing any field starts a distinct rating series.

## 8. Context and progression

Context capture is passive. It may read authoritative game state but cannot
grant items, place entities, advance research, or run simulation. Use a
monotonic watermark consisting of session_id, epoch_index, captured_tick, and
state_digest. Reject snapshots older than the prior finalized epoch.

Progression bands are coverage labels, not separate ratings in version 1:

| Band | Meaning |
| --- | --- |
| 0 | Bootstrap: hand mining, burner power, basic crafting |
| 1 | Early automation: electricity, belts, inserters, red/green science |
| 2 | Scaling: steel, oil entry, trains or comparable logistics |
| 3 | Advanced industry: chemicals, robots, later science |
| 4 | Launch-capable: rocket chain and mature infrastructure |
| 5 | Endgame: sustained science and high-throughput expansion |

The classifier uses stable state features and table tests. A session must not
move backward merely because inventory was consumed.

### 8.1 Factory progress versus agent performance

The underlying progress measure is expansion of the factory's sustainable
production possibility frontier. For a demand vector `d`, the factory has a
feasible set `F(s, T)` containing the orders it can supply within horizon `T`
from state `s`. Progress is an expansion of this set, or an improvement in the
latency, throughput, cost, or reliability of an existing order. The set is
allowed to shrink after depletion, damage, or reconfiguration; the record keeps
the observed state and does not silently convert a historical capability into a
current one.

Use a partial capability vector rather than a single ordinal as the primary
description:

```text
progress = (
    sustainable frontier tier,
    breadth of observed products and bundles,
    joint sustainable throughput,
    delivery reliability,
    infrastructure capacity
)
```

Science per minute and progression bands are useful projections of this vector,
not substitutes for it. Separate products measured in isolation do not prove a
joint capability, so mixed-demand orders are required to test the shape of the
frontier. The current runner persists per-epoch post-contexts, capability graph
snapshots, and deltas, plus an `observed_only` progress-vector summary in the
existing session notes field. It does not call a one-off delivery autonomous.

Agent performance is measured separately: frontier expansion per simulation
time, delivery efficiency, intervention cost, recovery behavior, and rating
confidence. This prevents a quickly assembled but fragile factory from being
confused with a genuinely capable one.

### 8.2 Commissioning, service, and qualification

Orders have distinct measurement phases:

1. **Commissioning** establishes whether a nearby product or dependency can be
   constructed and delivered at all. It uses a small request and is evidence of
   reachability, not sustainable capacity.
2. **Service** requests a sustained rate or mixed demand over repeated delivery
   windows. It establishes throughput and reliability from the persistent
   factory, with buffers treated as legitimate but finite infrastructure.
3. **Qualification** freezes the agent, applies a committed demand vector, and
   runs the factory for a defined autonomous window. Only this phase can issue
   an autonomous-capability certificate.

The current benchmark performs commissioning and service measurements. It does
not yet claim qualification. A future implementation should fork or checkpoint
the world at the end of construction, stop all agent actions, run warm-up and
service windows, record lower-bound throughput and reliability, then discard the
validation fork. The validation fork must not mutate the scored trajectory.

## 9. Progression-aware generation

### 9.1 Product metadata

Derive product metadata from pinned Factorio prototypes and recipes. Cache
enabling technologies, recipe depth, machine categories, ingredients and
fluids, craftability, base craft time, transport prerequisites, and
cyclic/catalyst behavior. Templates may allow or exclude products, but recipe
facts come from game data rather than a hand-maintained difficulty list.

### 9.2 Candidate mixture

Generate a bounded pool:

- **Consolidation**: unlocked products at increased quantity or sustained rate.
- **Frontier**: products one meaningful capability beyond current production.
- **Stress**: unlocked products that test power, logistics, or scaling.

Start with 40% consolidation, 40% frontier, and 20% stress, subject to coverage
requirements. Changing these weights requires a new benchmark version.

Frontier candidates target exactly one progression band above the observed
factory band (capped at endgame); consolidation and stress remain in the
observed band. The first epoch establishes a consolidation baseline. Before
ordinary rating-optimal selection resumes, later epochs must cover every
currently feasible mixture class and must prefer an unseen product within the
selected class. Candidate pools sample distinct feasible products before
repeating; consolidation includes unproduced same-band products while retaining
a bias toward installed production. This prevents a successful first production
line from collapsing the benchmark into that item forever.

### 9.3 Quantity and deadline

~~~text
baseline_rate = max(existing_rate, stage_reference_rate, epsilon)
target_rate = baseline_rate * pressure_multiplier
quantity = round_to_batch(target_rate * production_window_minutes)
~~~

Compute an analytic minimum time from transitive chain craft times, missing
production-category construction, and the complete prerequisite closure of
unavoidable research. This is a lower bound, not a competent-agent estimate.

Once calibration data exists, predict a successful reference-run completion
distribution and use a high conditional quantile as a feasibility guard:

~~~text
deadline = max(
    analytic_minimum_ticks * safety_factor,
    predicted_success_quantile_ticks,
)
~~~

The analytic lower bound catches impossible contracts. The empirical quantile
catches technically possible but pathological ones. Log them separately.

Every deadline must fit within remaining_session_simulation_ticks. Generation
is a pure deterministic function of template version, template ID, generation
seed, context, and game-data version.

### 9.4 Rejection policy

Reject candidates when:

- a product or recipe is absent from pinned game data
- required technology is unreachable within the horizon
- the analytic minimum exceeds the deadline
- required rate exceeds calibrated stage limits beyond the stress margin
- uncommitted inventory already covers the order, unless logistics is the task
- a recent product family exceeds its repetition cap
- features fall outside the official calibration envelope

Persist rejection reasons.

## 10. Contextual difficulty

A persistent factory makes fixed item difficulty invalid. The same circuit
order differs radically before and after a circuit bus exists.

Version 1 uses a scalar model:

~~~text
raw_difficulty =
    template_intercept
    + beta_raw dot normalized_raw_order_features

state_advantage =
    beta_state dot normalized_state_features

effective_difficulty = raw_difficulty - state_advantage
~~~

Important interactions should be explicit physical ratios:

- required rate / existing rate
- requested quantity / inventory
- missing technologies for this product
- missing machine categories for this chain
- estimated new power / spare capacity

Start with a small auditable feature set. Add terms only when held-out
calibration shows systematic residuals. Freeze feature definitions, clipping,
normalization, coefficients, covariance, and supported ranges in the
calibration manifest. Out-of-range epochs are flagged and excluded from
official rating unless that range is explicitly supported.

## 11. Outcome mapping

The state machine retains detailed results. The rating layer maps them globally:

~~~text
fulfilled                               -> win
completion_ratio <= partial_floor       -> loss
partial_floor < ratio < partial_ceiling -> draw
expired with zero or low delivery       -> loss
agent abandonment                       -> loss
infrastructure error                    -> unrated
invalid contract                        -> unrated
~~~

Initial thresholds are partial_floor = 0.25 and partial_ceiling = 0.90. They
remain useful for categorical reporting. Rating uses the continuous completion
score: the rater interpolates between the loss, draw, and win TrueSkill
posteriors, so 26% and 99% completion do not produce the same update. Exact
fulfillment remains a categorical win. Always retain raw completion ratio,
per-product delivery, and delivery timing so this approximation can be
recomputed or replaced.

## 12. Rating update

Hide inference behind:

~~~python
class ContractRater(Protocol):
    def initial_rating(self) -> CapabilityRating: ...

    def update(
        self,
        rating: CapabilityRating,
        difficulty_mean: float,
        difficulty_sigma: float,
        result: Literal["win", "draw", "loss"],
    ) -> CapabilityRating: ...

    def update_continuous(
        self,
        rating: CapabilityRating,
        difficulty_mean: float,
        difficulty_sigma: float,
        score: float,
    ) -> CapabilityRating: ...
~~~

Treat each epoch as a match between a persistent agent player and a virtual
contract player. The contract mean is effective_difficulty. Its uncertainty
includes calibration and extrapolation uncertainty. Update the agent posterior
and discard the virtual contract posterior.

Use a pinned, tested TrueSkill implementation or an audited local
implementation. Do not call this posterior conjugate Normal: TrueSkill uses
Gaussian message-passing approximations around non-Gaussian comparisons.

Required tests:

- golden results against the chosen reference
- a win raises mu and a loss lowers it
- near-rated contracts reduce uncertainty more than extreme mismatches
- uncertain contracts produce smaller updates
- draw handling
- finite, nonnegative uncertainty after 1,000 synthetic updates

Publish mu, sigma, and conservative_score = mu - 3 * sigma. Sort by conservative
score, while displaying wins, draws, losses, orders fulfilled, and coverage.

## 13. Adaptive selector

The official bank contains templates, private seeds, calibrated ranges, and
selection policy. It need not enumerate every exact order because context is
unique.

Each epoch:

1. Capture and freeze context.
2. Generate a bounded pool from private seeds.
3. reject infeasible and out-of-domain candidates.
4. Compute effective difficulty and uncertainty.
5. Estimate rating information gain.
6. Apply stage and product-family coverage constraints.
7. Score candidates.
8. Select with committed seeded randomness.
9. Persist and hash the complete epoch.

~~~text
score =
    w_info * expected_information_gain
    + w_coverage * coverage_deficit
    + w_novelty * family_novelty
    - w_repeat * recent_family_repetition
    - w_extrapolation * calibration_extrapolation
~~~

Information gain should favor difficulty near the current rating, but cannot
exclusively choose the closest item or the session will collapse into one
stage.

Sandbag resistance:

- freeze context before commitment
- cap inventory credit to a calibrated useful range
- use installed capacity and recent production, not inventory alone
- retain hidden candidate seeds
- report repeated destruction/rebuild patterns
- never make later contracts easier because useful infrastructure was discarded

### 13.1 Evidence-driven customer policy

The capability graph controls which products are plausible candidates; it is
not a hard scripted ladder. The online customer then makes three joint but
orthogonal decisions:

1. **Breadth:** choose a product using learning uncertainty, staleness,
   under-coverage, frontier value, and a recent-product penalty. An 80% hard
   rotation away from the immediately previous product prevents accidental
   single-item loops when alternatives exist.
2. **Service mode:** use a small commissioning order for products without
   evidence, a sustained throughput window for demonstrated production, or a
   consolidation order that tests cumulative capacity. Mixed orders are one
   service contract with independently sized product lines. Each line receives
   its own feature/difficulty evaluation; the committed contract difficulty is
   their mean plus a coordination term, matching mean per-line fulfillment.
3. **Pressure:** size each line from observed depot delivery rates, live 60/300
   second production rates, completion history, and rate uncertainty. A failed
   order may still be followed by more total units when evidence supports a
   longer service window; quantity does not mechanically increase just because
   the previous contract failed.

Cold-start quantity falls with recipe depth and its setup deadline grows with
recipe depth and missing technology. Consequently an unseen electronic circuit
is a small, generous commissioning request, not a plate-scale bulk order.
Sustained contracts use integer-aware delivery windows. High-volume contracts
retain approximately minute-scale cadence, while low-volume contracts use
fewer equal-duration windows with whole-item quotas (normally at least two
items per window). Quotas sum exactly to the requested quantity, so discrete
items cannot make perfect service mathematically impossible. All automated
traffic inside the service interval remains available to cadence scoring after
the nominal quantity is accepted; the accepted quantity and reward remain
capped. This prevents both end bursts and high-throughput early fills from
distorting the result.

The official online selector uses an evaluation adaptation of PLR/ACCEL rather
than importing their training replay buffers or claiming to reproduce their
learned-regret algorithms. A deterministic 20-order schedule assigns 50% of
orders to rating-near anchors, 30% to replay/consolidation, 15% to a one-edge
frontier, and 5% to a one-axis ACCEL-style mutation. Replay priority combines
intermediate completion, capability-path progress, uncertainty, staleness, and
breadth. ACCEL mutations change one local pressure axis of a demonstrated or
near-demonstrated order; they never jump arbitrarily deeper into the graph.
Every committed spec records the lane, reason, parent, mutation, line sizing,
and final rating distance.

The policy should be understood as measurement over the capability frontier,
not as a hidden ladder the agent must infer. Its useful actions are to expand
nearby capability, deepen sustainable throughput, compose multiple demands, or
revalidate stale evidence. Coverage and uncertainty can guide that choice, but
the policy remains runner-side and is never included in the agent prompt.

An attempted contract is audit history, not capacity evidence. Contract credit
and throughput sizing use only simulation-sourced traffic delivered by
inserters into customer depots. Direct agent insertion is drained and retained
as manual audit telemetry, but never changes fulfillment or capacity evidence.
The backend also retains automated totals and per-window delivery measurements
separately from sustained-service completion, so a late automated inventory
burst may have 100% raw coverage and still receive a lower service score. A
zero-delivery frontier attempt with capability progress is preferentially
replayed at lower pressure; it does not authorize a larger throughput request.
Transient automated depot rates are observational evidence only. A product
enters throughput selection after a sustained contract reaches at least 60%
service coverage; the existing 80% threshold remains the stronger reliability
requirement for stress selection.

`factory_band` is measured from the frozen persistent state and `target_band`
describes the requested probe. The legacy `stage_band` field aliases the target
band for old readers. Frontier eligibility is limited to one band/graph edge
beyond the measured factory envelope. Commissioning and service deadlines are
bounded between documented minima and a four-hour simulation maximum; a deep
or analytically enormous candidate is deferred instead of made nominally
feasible by a multi-day deadline.

For OpenCode, a provider `step_finish` with `reason:length` resumes the same
session and contract epoch. Repeated context continuations are not a turn or
intervention budget. Only an authoritative MCP terminal signal ends the order;
a clean or nonzero provider exit without that signal is an unrated
infrastructure outcome. Per-invocation reasons and continuation decisions are
persisted in the epoch audit artifact.

## 14. Persistent backend lifecycle

The current one-task-per-lease lifecycle is insufficient. Add methods equivalent
to:

~~~python
begin_contract_epoch(
    lease_id: str,
    expected_epoch_index: int,
    spec: ContractEpochSpec,
) -> ActiveContractState

finalize_contract_epoch(
    lease_id: str,
    epoch_index: int,
    commitment_hash: str,
) -> ContractEpochOutcome

get_contract_session_state(
    lease_id: str,
) -> ContractSessionState

finalize_contract_session(
    lease_id: str,
) -> ContractSessionSummary
~~~

Required behavior:

- one open epoch per lease
- monotonically increasing epoch indexes
- idempotent begin/finalize under identical request IDs
- rejection of a second active order
- active customer state cleared after finalization
- world, force, research, inventory, and entities preserved
- separate session and epoch tick totals
- finalized records retained through session end
- privileged benchmark HTTP access only, never agent tools

Tests must prove epoch N+1 inherits the factory produced in epoch N.

## 15. Persistent agent runner

Create scripts/adaptive_contract_benchmark.py. It retains one backend lease and
one model conversation across epochs.

~~~python
class AgentSession(Protocol):
    async def start(self, system_prompt: str, tool_manifest: ToolManifest) -> None: ...
    async def run_epoch(self, order_prompt: str) -> AgentEpochTelemetry: ...
    async def close(self) -> None: ...
~~~

Runner loop:

~~~text
acquire one lease
start one agent conversation
load or initialize rating
repeat:
    capture context
    select and commit a contract
    begin epoch
    send the new order and observable state
    run until outcome or the session wall-clock failsafe
    finalize epoch
    map outcome and update rating when ratable
    persist the record atomically
    evaluate stopping rule
finalize session
release lease
close conversation
~~~

Record model turns, tool calls, tokens where available, model seconds, tool
seconds, paused wall seconds, and transport errors. Provider harnesses implement
AgentSession; common policy never branches on provider.

Session and audit JSON use a same-directory temporary file followed by
`os.replace`. The temporary file is flushed and synced before replacement;
Windows sharing violations receive a bounded exponential backoff, and the
temporary path is cleaned on both success and failure. A persistent replace
failure is an I/O error, not a customer-order loss.

## 16. Calibration

### 16.1 Records and anchors

Retain participant identity, factory seed, template and generation seed, context
and order features, outcome, completion ratio, simulation ticks, interventions,
and infrastructure validity.

Collect overlapping runs from scripted baselines, intentionally limited
scripts, at least two materially different model/harness configurations,
repeated participants across seeds, and repeated templates across contexts.
Participants need overlapping contracts, and contracts need overlapping
participants, or the scale is not identifiable.

### 16.2 Fit and manifest

Use offline batch maximum a posteriori fitting with NumPy and SciPy. Jointly fit
participant abilities, template intercepts, and contextual coefficients under
regularizing priors. Fix location and scale explicitly, for example:

~~~text
mean(anchor participant abilities) = 0
performance scale beta = 1
~~~

Split validation by both factory seed and participant identity. Row-level
random splits leak repeated factories and behavior.

The immutable calibration manifest contains:

- training-data digest
- game and mod versions
- feature schema and template bank versions
- outcome thresholds
- coefficients and normalization statistics
- parameter covariance or bootstrap uncertainty
- supported feature ranges
- held-out metrics
- implementation commit

### 16.3 Acceptance gates

Official scoring begins only when:

- held-out probabilities pass reliability and Brier-score review
- no progression band has a large systematic residual
- controlled tests are monotonic in quantity and deadline pressure
- repeated-seed estimates are stable
- extrapolation is below the published limit
- synthetic parameter-recovery tests pass

Do not promise a fixed small sample size. Report intervals and collect data
until gates pass.

## 17. Session stopping

By default the generator continues issuing customers until either five orders
are partially delivered, expire, or are abandoned, or 24 hours of runner wall
time elapse. The failed-delivery threshold is configurable. Sigma, epoch, tick,
turn, and intervention limits are disabled unless an experiment explicitly
enables them. Optional rating-convergence limits still require mandatory
coverage; failure and wall-clock stops do not.

An unrecoverable infrastructure failure interrupts rather than completes the
session and does not increment failed deliveries. Wall-clock is a generous
operational failsafe only. Low-interactivity model wall time is not evidence
that wall time belongs in contract difficulty.

## 18. Published result schema

Publish:

- exact participant/model snapshot and harness identity
- prompt, tool manifest, and inference-setting hashes
- benchmark, bank, calibration, game, and mod versions
- rating mu, sigma, and conservative score
- wins, draws, losses, and unrated epochs
- orders fulfilled and units delivered
- fulfillment by progression band
- simulation ticks and interventions
- median and tail first-delivery and completion ticks
- model, tool, paused, and runner wall-clock seconds
- extrapolation and infrastructure-error counts
- per-epoch post-context, capability-graph snapshots, and capability deltas
- an `observed_only` progress vector and portfolio evidence summary in session
  notes; these are evidence hooks, not autonomous-capability certificates
- ordered epoch commitment hashes

The session record remains valid for existing readers because the summary uses
the already published `notes` field. Consumers that need machine-readable
details should parse the `progress_vector_v1=` and
`portfolio_evidence_v1=` note entries, while using the epoch records as the
authoritative source for detailed evidence.

## 19. PLR training policy

Prioritized Level Replay schedules training; it does not rate official runs.

Level identity includes training bank version, template, generation seed,
factory checkpoint or initial seed, context digest, and difficulty digest.

~~~python
class ReplayLevelRecord(BaseModel):
    level_id: str
    attempts: int
    last_attempt_step: int
    outcome_ema: float
    value_error_ema: float | None
    learning_progress_ema: float
    staleness: float
    invalid_count: int
~~~

When the policy exposes a value estimate, prioritize absolute value error or
positive value loss. Otherwise use checkpoint-to-checkpoint change in success
probability as a slower learning-progress proxy.

Initial sampling mixture:

~~~text
0.60 * normalized_learning_signal
+ 0.20 * normalized_staleness
+ 0.10 * underrepresented_stage
+ 0.10 * uniform_mass
~~~

Reserve probability for unseen levels, cap any one level, decay old failures,
and quarantine repeatedly invalid levels. Test deterministic replay, nonzero
unseen probability, caps, staleness, and quarantine.

## 20. ACCEL training policy

ACCEL proposes nearby harder levels after valid ones are learned. Allow bounded,
interpretable mutations:

- quantity multiplier
- deadline adjustment within calibration limits
- one recipe-graph product step
- one missing prerequisite
- one resource-layout or factory-seed family perturbation
- one logistics constraint

Reject infeasible, duplicate, multi-mutation, trivial-inventory, or
out-of-envelope levels.

Use a same-level reference gap:

~~~text
regret =
    reference_success_probability
    - current_policy_success_probability
~~~

The reference is a stronger frozen checkpoint, best-known policy, or bounded
planner evaluated on the same level.

ACCEL output remains training-only. Official promotion requires shadow anchor
evaluation, feasibility review, recalibration, held-out validation, and a new
immutable bank version.

## 21. Tests

Add:

- tests/envd/test_contract_features.py
- tests/envd/test_contract_generator.py
- tests/envd/test_contract_rating.py
- tests/envd/test_contract_selector.py
- tests/envd/test_contract_calibration.py
- tests/envd/test_contract_curriculum.py
- tests/envd/test_adaptive_contract_backend.py
- tests/scripts/test_adaptive_contract_benchmark.py

Property tests verify deterministic generation and commitments, monotonic
quantity/deadline difficulty, nonincreasing difficulty from relevant inventory
or prerequisites, horizon compliance, immutable committed specs, and finite
rating uncertainty.

Statistical tests generate agents and contracts with known parameters and
require recovery of rank ordering, approximate coefficients, held-out
probability calibration, and expected rating coverage.

A live Factorio test runs two epochs, builds in epoch 1, and proves that
infrastructure, research, and inventory survive into epoch 2 while active order
state and epoch counters reset.

Every harness test keeps one conversation across two orders, verifies stable
tool schemas, confirms task completion does not release the lease, and
classifies provider failures without creating losses.

## 22. Implementation sequence and gates

### Stage 1: Generation substrate

Implement prototype metadata, analytic feasibility, deterministic templates,
and commitment hashing.

Gate: generator unit and property tests pass for the pinned game version.

### Stage 2: Context and identity

Implement snapshots, state digests, progression bands, features, and participant
hashing.

Gate: repeated snapshots are deterministic and band fixtures pass.

### Stage 3: Persistent backend

Implement epoch endpoints and session state while preserving the factory.

Gate: two-epoch live persistence and endpoint idempotency pass.

### Stage 4: Uncalibrated runner

Implement persistent AgentSession and collect raw outcomes with a broad fixed
candidate policy. Label scores experimental.

Gate: multiple harnesses produce complete reconstructable records.

### Stage 5: Calibration

Collect anchors, fit the contextual model, validate, and publish a manifest.

Gate: every calibration acceptance condition in section 16 passes.

### Stage 6: Rating and adaptive selection

Integrate TrueSkill, contract uncertainty, information gain, and coverage.

Gate: reference golden tests and synthetic end-to-end recovery pass.

### Stage 7: Official pilot

Freeze a private seed bank and run without changing parameters. Measure
repeatability, uncertainty reduction, harness effects, extrapolation, and
infrastructure failures.

Gate: publish diagnostics and explicitly approve a benchmark version. Changed
policy must receive a new version.

### Stage 8: PLR and ACCEL

Add training curricula after official measurement is stable.

Gate: training cannot read private evaluation seeds or write official
calibration artifacts.

## 23. Non-goals for version 1

- one rating shared across different tool manifests
- public per-product or per-stage skill vectors
- online mutation of official evaluation
- wall-clock speed as success
- per-item ordinal thresholds
- claims of stable ratings after a handful of epochs
- automatic promotion of generated training levels

## 24. Known limitations

1. Scalar ability hides differences in planning, logistics, recovery, and
   scaling. Stage and family breakdowns remain necessary.
2. Adaptive tests are path-dependent. Seeded policy and full records make them
   auditable, not identical.
3. Context is partial. Calibration residuals must drive conservative feature
   revisions.
4. TrueSkill is approximate and cannot repair a bad difficulty model.
5. Game, mod, tool, prompt, harness, and model changes can stale calibration.
6. Analytically valid generated contracts can still be unnatural.
7. PLR and ACCEL can overfit without diversity and held-out evaluation.
8. Long-horizon competence remains expensive to measure even with adaptive
   selection.

This design favors reconstructability and calibrated uncertainty over a
superficially simple Elo number. Each policy remains replaceable behind a
versioned interface so future evidence can improve generation, calibration, or
inference without rewriting customer delivery accounting.
