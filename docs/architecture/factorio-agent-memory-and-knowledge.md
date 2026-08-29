# Factorio agent memory and knowledge affordances

Status: design proposal for the next evaluation iteration

## 1. Decision

Long-horizon Factorio evaluation should not assume that a model has memorized
Factorio, the installed game version, or FLE's API. The environment should
offer versioned, callable references for mechanics and tools, plus an optional
model-managed memory workspace. These are separate affordances and must be
reported separately in every run.

The capability graph and adaptive order ladder remain useful, but neither
should turn the environment into a scripted tutorial:

- The capability graph describes dependencies and records demonstrated
  progress. It informs customer continuity and long-horizon diagnostics. It is
  not a hard boundary on which products the customer may request.
- The adaptive ladder varies quantity and deadline pressure for a chosen
  product. It supplies the repeated observations needed to estimate ability.
- The customer may issue a remote stretch order. If the agent makes meaningful
  progress toward it, the next order should preserve that direction rather
  than moving the objective farther away.

This gives the agent an open factory and open planning problem while preventing
the customer from behaving as if failure were evidence that a harder,
unrelated product is appropriate.

## 2. Problems being separated

The current system combines several distinct sources of difficulty:

1. **Game knowledge**: recipes, research, machine categories, fluids, power,
   ratios, and progression mechanics.
2. **Environment knowledge**: FLE tools, argument types, entity semantics,
   depot behavior, execution limits, and error recovery.
3. **Working memory**: what this agent already built, what failed, reusable
   code, locations, bottlenecks, and the current plan.
4. **Customer pressure**: product choice, quantity, and deadline.
5. **Planning ability**: converting available facts and persistent state into
   a working factory over a long horizon.

An evaluation that withholds the first three measures a mixture of recall,
harness survival, and planning. That can be a valid ablation, but it should not
be the only evaluation mode or be mistaken for pure Factorio capability.

## 3. Knowledge surfaces

### 3.1 Required API reference

Every normal evaluation harness should expose the same callable FLE reference.
This is part of the action interface, not an optional strategy hint. It must
cover:

- tool names, signatures, accepted enums, and return shapes;
- the distinction between `Position`, `Entity`, `Prototype`, and recipe IDs;
- representative error cases and the corrective action for each;
- parallel and programmatic tool-calling behavior;
- tick advancement and observation semantics;
- customer depot positions, immutable sink behavior, and delivery receipts;
- response truncation and pagination behavior.

The reference must be generated or tested against the active tool manifest so
it cannot silently drift from the implementation.

### 3.2 Authoritative game-data reference

The game-data exporter should be queryable through narrow tools rather than
requiring the model to reconstruct the technology tree from memory. Suggested
operations are:

```text
factorio_search_reference(query, kinds?, limit?, cursor?)
factorio_read_reference(document_id, section?, cursor?)
factorio_get_recipe(item_or_recipe_id)
factorio_get_technology(technology_id)
factorio_get_unlock_path(item_or_recipe_id)
factorio_get_machine_requirements(recipe_id)
```

Recipe, prototype, and technology answers should come from the exact Factorio
export used by the environment. Search results should include canonical IDs so
models do not have to guess names such as `ArtilleryShell`.

This reference supplies facts, not a prescribed plan. Knowing that plastic
requires petroleum gas and a chemical plant still leaves the agent responsible
for designing oil extraction, refining, transport, power, and production.

### 3.3 Optional strategy guide

A separate guide corpus may explain mechanics and common approaches in prose:

- bootstrapping power and automation;
- research and science-pack progression;
- diagnosing stalled machines and power networks;
- fluids and oil processing;
- scaling, buffering, transport, and bottlenecks;
- recovery from partially completed builds.

Guide documents must carry source, license, Factorio version, and content hash.
Generated game data remains authoritative when a guide disagrees with it.
Guides should explain alternatives and tradeoffs rather than provide one
benchmark-specific solution trajectory.

Guide access is an evaluation flag. It must never be silently inserted into a
system prompt or hidden inside a harness-specific implementation.

## 4. Model-managed memory

The memory system is a per-session, sandboxed notebook owned by the model. It
persists across customer orders and context compactions but not across
independent benchmark runs unless an evaluation explicitly enables cross-run
memory.

The minimum interface is:

```text
memory_list(prefix?, cursor?)
memory_read(key)
memory_write(key, content, expected_revision?)
memory_delete(key, expected_revision?)
memory_search(query, limit?, cursor?)
```

Recommended namespaces are:

- `plan/current`: current objective, next actions, and blockers;
- `factory/assets`: important entity groups, coordinates, and capacities;
- `factory/capabilities`: what is working versus merely attempted;
- `lessons`: errors, corrected API usage, and failed approaches;
- `library`: model-written reusable programs and construction patterns;
- `orders/<epoch>`: concise outcome and unfinished work for an order.

Memory content is untrusted model output. It cannot alter contracts, ratings,
leases, tool permissions, or authoritative observations. All mutations are
revisioned and included in the trace. The store should enforce byte and entry
limits for operational safety, but those limits are harness parameters rather
than intervention budgets.

### 4.1 Active management

Providing a key-value store is insufficient if the harness never gives the
model a natural opportunity to maintain it. The harness should add memory
checkpoints at lifecycle boundaries:

1. Before an expected context compaction, ask the model to persist durable
   plans, discoveries, code, and unresolved failures.
2. After compaction, expose the memory index and allow selective reads instead
   of injecting the entire store.
3. At order finalization, ask for a short handoff covering delivered work,
   capability progress, and the next likely step.
4. At the next order, preserve the same memory store and agent session.

If provider-side compaction cannot emit a pre-compaction hook, order-boundary
checkpoints still provide a reliable minimum. The system may generate a
read-only index, but it should not rewrite the model's conclusions on its
behalf.

## 5. Capability graph

The capability graph is environment evidence, not agent memory. Nodes represent
technologies, recipes, machine classes, resources, power, logistics, and
delivered products. Edges represent factual prerequisites from exported game
data. Each node records evidence such as:

- locked, unlocked, constructed, producing, or delivered;
- first and latest evidence ticks;
- stable and peak production rates;
- related order attempts and delivered quantities;
- prerequisite distance from the current factory snapshot.

The graph has three jobs:

1. Explain how far the factory progressed during a failed frontier order.
2. Identify a coherent follow-up target or prerequisite when continuity is
   preferable.
3. Supply contextual features for difficulty calibration and later analysis.

It should not forbid experimentation beyond the graph frontier. A configurable
stretch probability may deliberately select a more remote objective. The full
dependency distance and selection reason must be recorded when that happens.

Graph visibility is also configurable. The customer always uses the privileged
graph; the agent may receive no graph, a factual prerequisite query, or a
summarized progress view depending on the evaluation mode.

## 6. Minimal customer policy

Avoid a large curriculum state machine. The customer only needs the previous
outcome, capability delta, rating, and product ladder state.

```text
if previous order was fulfilled:
    increase pressure on that product or choose a new frontier/stretch target
elif capability progress occurred toward the failed product:
    repeat the same product or a close dependency with recalculated difficulty
elif partial delivery occurred:
    repeat the product near demonstrated capacity
else:
    reduce pressure or choose one prerequisite on the same dependency path
```

Random exploration remains allowed, but a failure cannot cause an unrelated
increase in prerequisite distance. A remote stretch failure should therefore
produce continuity, recovery, or backoff, not another remote draw.

The ladder is local to a product and factory snapshot. It brackets quantity and
deadline around observed results. The capability graph selects direction and
measures movement; the ladder controls pressure within that direction. They do
not need a shared mastery state or a complex controller.

A frontier order that expires after unlocking several dependencies remains a
rating loss if delivery was the committed objective. Its capability delta is
used only to choose the follow-up. The repeated order starts from a stronger
snapshot and therefore receives newly calculated contextual difficulty. This
preserves outcome integrity while recognizing long-horizon work.

## 7. Training and evaluation modes

Represent affordances as independent flags rather than one ambiguous
"assisted" mode:

| Profile | API reference | Game-data reference | Strategy guide | Session memory |
| --- | --- | --- | --- | --- |
| Recall baseline | Yes | No | No | No |
| Grounded | Yes | Yes | No | No |
| Stateful grounded | Yes | Yes | No | Yes |
| Guided | Yes | Yes | Yes | Yes |

The API reference remains present in all normal profiles because undocumented
tool syntax is harness difficulty. A separate intentionally undocumented API
ablation may exist, but it must say so explicitly.

Training can mix profiles to answer different questions:

- teach basic tool grounding with API and game-data references;
- train retrieval decisions without injecting large documents;
- train memory maintenance over order and compaction boundaries;
- distill successful guided trajectories into an unguided policy;
- compare the same model and seeds across affordance profiles.

Every participant identity must include hashes for the API reference, game-data
export, guide corpus, memory implementation, initial memory state, and graph
visibility policy. Otherwise scores from materially different environments can
be mistaken for comparable results.

## 8. Scoring and attribution

Customer deliveries remain the authoritative success signal. Research,
construction, memory writes, document reads, and capability-graph movement do
not directly earn TrueSkill wins.

Retain the following companion metrics:

- orders fulfilled and total units delivered;
- prerequisite nodes crossed per frontier attempt;
- same-target recovery success;
- reference queries and documents read;
- memory reads, writes, retained bytes, and stale-memory corrections;
- compactions survived without losing the active plan;
- rating by affordance profile.

The adaptive ladder supplies repeated task outcomes near the model's current
ability. The graph contributes contextual difficulty features, including
dependency distance and achieved state advantage. Neither should replace
offline calibration of contract difficulty.

## 9. Risks and imperfections

1. A strategy guide changes the capability being measured. That is intentional
   only when its profile is explicit.
2. Memory can preserve incorrect conclusions. Revision history and
   authoritative observations make errors inspectable but do not eliminate
   them.
3. Retrieval quality can become a hidden harness advantage. All harnesses need
   identical tools, corpus versions, limits, and response semantics.
4. Capability graphs omit spatial layout, congestion, resource geography, and
   the cost of repairing poor architecture. These remain planning difficulty.
5. Reissuing a frontier objective may overfocus a hopeless route. Stretch
   distance, capability delta, and elapsed wall time should bound continuity.
6. Adaptive orders make runs path-dependent. Seeded selection logs and
   calibrated difficulty are required, and fixed holdout profiles remain useful
   for cross-model comparisons.
7. Models could intentionally fail to obtain easier orders. The failed outcome
   must remain in the rating history, and follow-up difficulty must be committed
   from the new snapshot rather than retroactively changing the failed task.

## 10. Implementation sequence

1. Audit the current MCP/tool documentation against the actual manifest and
   make API lookup identical across native, Hermes, and OpenCode harnesses.
2. Expose exact recipe, prototype, technology, unlock-path, and machine queries
   from the versioned game-data export.
3. Add the revisioned session-memory service and order-boundary checkpoint
   prompts; keep it disabled by default until traces prove persistence.
4. Materialize capability evidence from existing snapshots, research events,
   production telemetry, and delivery receipts.
5. Change customer follow-up selection to use capability delta plus the local
   order ladder, retaining an explicitly logged stretch probability.
6. Run matched-seed ablations across grounded, stateful grounded, and guided
   profiles before deciding which profile becomes the primary benchmark.
