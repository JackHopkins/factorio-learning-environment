# Build Mode Prompt/Control Design Spec

Status: Draft for implementation  
Last Updated: 2026-02-23  
Scope: `run_with_video.py` prompt orchestration and mode transitions

## 1. Purpose
Define an unambiguous design for splitting responsibilities between:
- `orchestrator` mode (global planning/fixing/connecting/delegating)
- `build` mode (single-module scoped construction)

This document is normative. Keywords `MUST`, `MUST NOT`, `SHOULD`, and `MAY` are intentional requirements.

## 2. Goals
1. Keep existing high-value base prompt content (types, manual, patterns, cookbook) intact.
2. Enforce strict separation of concerns between orchestrator and build mode.
3. Switch modes via explicit agent command, not step thresholds.
4. Use strict pre-switch validation (including exact coordinate world checks).
5. Support build completion and build give-up return paths.
6. Persist active build contract state to avoid mode desync.

## 3. Non-Goals
1. Introducing additional specialized modes (for example, connector-only mode).
2. Refactoring broader FLE agent architecture outside run/video pipeline.
3. Automatic module graph inference from all entities in this iteration.

## 4. Definitions
1. **Orchestrator mode**: global policy mode; can fix, connect, and optionally direct-build.
2. **Build mode**: scoped module mode; receives one active build contract.
3. **Active build request**: accepted `BUILD_MODE_REQUEST` payload currently in effect.
4. **Pre-switch validation**: schema + world checks performed before switching to build mode.
5. **Exact coordinate check**: equality match on coordinates; zero tolerance.

## 5. Prompt Structure

## 5.1 Base Prompt
The base system prompt remains the existing FLE prompt (including types/tool manuals/patterns/cookbook).

## 5.2 Orchestrator Overlay
Orchestrator overlay MUST include:
1. Role: fix + connect + delegate.
2. Rule: direct build is allowed at orchestrator discretion.
3. Rule: delegation uses `BUILD_MODE_REQUEST` first-line command.
4. Rule: return handling for `BUILD_MODE_DONE` and `BUILD_MODE_GIVE_UP`.
5. Module registry policy:
- existing modules only
- verified facts only
- no placeholder values (`unknown`, `UNCONFIRMED`)
- missing facts listed under `missing_contracts`

## 5.3 Build Overlay
Build overlay MUST include:
1. Scoped execution constraints for one module zone.
2. Contract adherence (input/power/output requirements).
3. Verification requirement before DONE.
4. No global module registry dump in build mode prompt.

Build overlay MUST NOT include orchestrator-wide module registry context.

## 5.4 Explicit Prompt Removals Agreed
The following MUST be removed from build-mode prompt text:
1. `- Long-horizon planning`
2. `- DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off`
3. `- Ensure that your factory is arranged in a grid`
4. `- have at least 10 spaces between different factory sections`
5. `### Module Registry (Reference)` block

From orchestrator prompt guidance, remove:
1. `### Entities` subsection under observation explanation.

## 6. Mode Control Commands

All control commands MUST be in the first line of generated policy code as a Python comment.

Valid commands:
1. `# BUILD_MODE_REQUEST {json}`
2. `# BUILD_MODE_DONE {json}`
3. `# BUILD_MODE_GIVE_UP {json}`

If first line does not match these commands, treat output as normal executable policy code.

## 6.1 Command Parsing
Parser MUST:
1. Read first non-empty line only.
2. Match exact prefix `# BUILD_MODE_* `.
3. Parse trailing JSON object.
4. Reject malformed JSON as command parse failure.

## 7. Unified Build Request Schema

One envelope schema MUST be used for all module types:

```json
{
  "version": 1,
  "request_type": "BUILD_MODE_REQUEST",
  "request_id": "string",
  "module_type": "iron_mine_electric | smelter_coal",
  "zone": {"x_min": "number", "x_max": "number", "y_min": "number", "y_max": "number"},
  "interfaces": {"inputs": [], "outputs": []},
  "power": {"required": "boolean", "anchors": [], "max_connection_distance_tiles": "number"},
  "constraints": {
    "inside_zone_only": "boolean",
    "reject_if_required_interface_missing": "boolean",
    "allow_remove_existing_entities": "boolean"
  },
  "success_criteria": {
    "must_have_power": "boolean",
    "must_consume_inputs": [],
    "must_output_item": "string",
    "min_output_per_sec": "number",
    "consecutive_checks": "integer"
  },
  "module_spec": {"module_spec_version": 1, "data": {}},
  "notes": "string"
}
```

## 7.1 Module Type Specialization
1. `iron_mine_electric`
- output `ore_out` REQUIRED
- power REQUIRED
- module_spec MUST include resource + build_target

2. `smelter_coal`
- inputs `ore_in` and `coal_in` REQUIRED
- output `plate_out` REQUIRED
- power REQUIRED
- module_spec MUST include recipe + build_target

## 8. Pre-Switch Validation (Before Entering Build Mode)

All checks below MUST pass to enter build mode.

## 8.1 Schema/Envelope Checks
1. JSON parse success.
2. Required fields present.
3. Enum values valid.
4. Zone bounds valid (`x_min < x_max`, `y_min < y_max`).

## 8.2 Module-Type Checks
1. Required interfaces per module_type exist.
2. Required module_spec keys exist.

## 8.3 Exact World Checks (Zero Tolerance)
No radius or near checks are allowed.

1. Required input lines:
- For each required input, entity/line MUST exist at exact coordinate.
- Direction MUST match exactly.
- Lane-side MUST match exactly.

2. Required power anchors:
- Anchor entity/network point MUST exist at exact coordinate.

3. Required output handoff:
- Position MUST match exact coordinate.
- Direction/lane contract MUST be achievable at exact coordinate.

4. Required-interface gate:
- If `reject_if_required_interface_missing = true`, any missing required interface MUST reject.

## 8.4 Rejection Behavior
On failure, system MUST:
1. Stay in orchestrator mode.
2. Emit/record:

```json
{
  "type": "BUILD_MODE_REJECTED",
  "request_id": "string",
  "errors": ["string", "..."]
}
```

3. Inject rejection payload into next orchestrator context.

## 9. Build Mode Runtime and Exit

## 9.1 Request Step Accounting
The orchestrator step that emits `BUILD_MODE_REQUEST` MUST count as a normal step.
The mode switch applies to the next model call.

## 9.2 Active Build Request State
System MUST persist:
1. `active_build_request` payload
2. `active_build_request_id`
3. current mode

This state MUST survive per-step execution failures and retries during the run.

## 9.3 Build Completion
Build mode completion command:

```json
{
  "version": 1,
  "request_id": "string",
  "status": "success | partial | failed",
  "verification": {},
  "handoff": {},
  "notes": "string"
}
```

On accepted DONE:
1. Exit build mode.
2. Clear active request.
3. Return to orchestrator with DONE payload injected into context.

## 9.4 Build Give-Up
Build mode give-up command:

```json
{
  "version": 1,
  "request_id": "string",
  "status": "impossible",
  "reason": "string",
  "evidence": {},
  "recommended_orchestrator_action": "string"
}
```

Rules:
1. `reason` MUST be non-empty string.
2. `request_id` MUST match active request.
3. On accepted GIVE_UP:
- Exit build mode
- Clear active request
- Return payload to orchestrator context

Pre-switch failures MUST NOT use GIVE_UP. They MUST use REJECTED.

## 10. Build Mode Context Policy
Build mode prompt context MUST include:
1. Base system prompt (minus agreed removals).
2. Build overlay.
3. Accepted build request JSON.
4. Current inventory.
5. Local zone context needed for scoped execution.
6. Verification signal(s) needed for DONE criteria.

Build mode prompt context MUST NOT include:
1. Global module registry dump.
2. Unrelated module summaries.

## 11. Module Registry Policy (Orchestrator)
Registry entries MUST:
1. Represent existing modules only.
2. Contain verified facts only.
3. Avoid placeholders (`unknown`, `UNCONFIRMED`).
4. Put absent-but-needed data into `missing_contracts`.

## 12. Logging and Observability
System MUST log mode events:
1. BUILD_MODE_REQUEST accepted
2. BUILD_MODE_REJECTED
3. BUILD_MODE_DONE
4. BUILD_MODE_GIVE_UP

Each event MUST include:
1. run version
2. step number
3. request_id (if applicable)
4. payload snapshot
5. validation errors (if applicable)

Prompt snapshots SHOULD be written when mode changes.

## 13. Failure Handling
1. Malformed command JSON: treat as normal code + log parse warning.
2. Invalid request schema: reject switch.
3. DONE/GIVE_UP without active request: ignore command + inject orchestrator warning.
4. Request ID mismatch: ignore command + inject orchestrator warning.

## 14. Acceptance Criteria
Implementation is complete only when:
1. Command-based switching replaces step-threshold switching.
2. Strict exact-position pre-checks gate all BUILD_MODE_REQUEST transitions.
3. Build prompt excludes module registry and includes accepted request context.
4. DONE and GIVE_UP return correctly to orchestrator.
5. Mode-event logs are persisted.
6. Viewer/API can show exact prompts and mode transitions for a validation run.

## 15. Out of Scope (This Iteration)
1. Automatic generation of complete module registry from world entities.
2. Additional module types beyond `iron_mine_electric` and `smelter_coal`.
3. New dedicated connector mode.

