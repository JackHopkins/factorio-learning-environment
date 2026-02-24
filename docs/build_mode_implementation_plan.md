# Build Mode Implementation Plan

Status: Execution plan  
Last Updated: 2026-02-23  
Depends on: `docs/build_mode_design_spec.md`

## 1. Objective
Implement command-driven orchestrator/build mode transitions with strict pre-switch validation and scoped build prompt context, while preserving existing high-value base prompt content.

## 2. In-Scope Deliverables
1. Replace step-threshold switching with command-based switching.
2. Implement unified `BUILD_MODE_REQUEST` parser/validator.
3. Implement strict exact-coordinate world prechecks.
4. Implement `BUILD_MODE_REJECTED` path.
5. Implement `BUILD_MODE_DONE` and `BUILD_MODE_GIVE_UP` return paths.
6. Persist and log `active_build_request` state.
7. Apply agreed prompt removals and overlay updates.
8. Validate with a short run and viewer/API evidence.

## 3. Out of Scope
1. Additional mode types beyond orchestrator/build.
2. Automatic module registry inference from raw entities.
3. Broad refactors of non-run video evaluation path.

## 4. Files to Modify
Primary:
1. `run_with_video.py`
2. `fle/agents/gym_agent.py`

Likely support additions:
1. `viewer.py` (only if extra mode-event API output is needed)
2. `docs/build_mode_design_spec.md` (already added)
3. `docs/build_mode_implementation_plan.md` (this file)

Optional tests (recommended):
1. `tests/eval/...` new tests for command parse and mode transition behavior
2. `tests/gym_env/...` if any local context extraction helper needs tests

## 5. Implementation Phases

## Phase A: Prompt Policy Finalization
Tasks:
1. Keep base prompt content (types/manual/patterns/cookbook).
2. Keep orchestrator overlay with fix+connect+delegate behavior.
3. Ensure module registry policy is existing-only and verified-facts-only.
4. Remove agreed strings from build mode prompt:
- `- Long-horizon planning`
- `- DON'T REPEAT YOUR PREVIOUS STEPS - just continue from where you left off`
- `- Ensure that your factory is arranged in a grid`
- `- have at least 10 spaces between different factory sections`
- `### Module Registry (Reference)` block
5. Remove `### Entities` section from generic observation guidance.

Exit criteria:
1. Prompt generation functions produce expected overlays.
2. No disallowed strings remain in build mode output.

## Phase B: Command Parsing Infrastructure
Tasks in `run_with_video.py`:
1. Add first-line command parser:
- input: policy code string
- output: `{command_name, payload}` or `None`
2. Supported commands:
- `BUILD_MODE_REQUEST`
- `BUILD_MODE_DONE`
- `BUILD_MODE_GIVE_UP`
3. Parse only first non-empty line.
4. Trailing JSON object required for recognized command.
5. Malformed JSON = command parse failure; treat as normal code path.

Exit criteria:
1. Parser deterministic for valid/invalid examples.
2. No mode change occurs from malformed command lines.

## Phase C: Unified Request Schema Validation
Tasks:
1. Implement envelope validation function for `BUILD_MODE_REQUEST`.
2. Implement module-type validator:
- `iron_mine_electric`
- `smelter_coal`
3. Enforce required keys and enums exactly per spec.
4. Enforce zone shape and mandatory contract fields.

Exit criteria:
1. Invalid request payloads yield explicit error list.
2. Valid payloads pass both envelope and module checks.

## Phase D: Strict Pre-Switch World Checks (Exact Coordinates)
Tasks:
1. Add world-check helpers for required interfaces:
- exact input line coordinate existence
- exact direction match
- exact lane-side match
2. Add exact power anchor check.
3. Add exact output handoff feasibility check.
4. Enforce zero tolerance (no near/radius substitution for location checks).
5. Respect `reject_if_required_interface_missing`.

Exit criteria:
1. Any mismatch blocks mode switch.
2. Error payload explains exact failing contract field.

## Phase E: Transition State Machine
Tasks:
1. Remove dependency on `FLE_PROMPT_SWITCH_STEP` for authoritative switching.
2. Drive mode switch only from accepted `BUILD_MODE_REQUEST`.
3. Request step still counts as executed step.
4. Introduce persistent runtime state:
- `current_mode`
- `active_build_request`
- `active_build_request_id`

State transitions:
1. `orchestrator` + accepted request -> `build`
2. `orchestrator` + rejected request -> remain `orchestrator`
3. `build` + DONE (matching request_id) -> `orchestrator`
4. `build` + GIVE_UP (matching request_id) -> `orchestrator`

Exit criteria:
1. No transition occurs without valid command + validation.
2. Request ID mismatch does not terminate active build request.

## Phase F: Rejection / Return Payload Injection
Tasks:
1. On pre-switch failure, inject `BUILD_MODE_REJECTED` payload into orchestrator context.
2. On DONE, inject completion payload summary into orchestrator context.
3. On GIVE_UP, inject reason payload summary into orchestrator context.
4. Ensure payload includes `request_id`.

Exit criteria:
1. Orchestrator gets machine-readable feedback in next step context.
2. Context includes correct event type and payload data.

## Phase G: Build Context Scoping
Tasks:
1. Build-mode prompt should include:
- base prompt (after agreed removals)
- build overlay
- accepted request payload
- inventory + zone-local context
2. Build-mode prompt should exclude:
- global module registry dump
- unrelated module details

Exit criteria:
1. Exact prompt payload for build step contains request scope but no global registry block.

## Phase H: Logging / Observability
Tasks:
1. Log each mode event with:
- version
- step
- command type
- request_id
- payload
- validation errors (if any)
2. Persist mode-event logs:
- file logs under trajectory dir
- DB meta if feasible in current pipeline
3. Keep prompt snapshots on mode transitions.

Exit criteria:
1. Mode timeline can be reconstructed from logs without ambiguity.

## 6. Detailed Task Checklist (Per File)

## `run_with_video.py`
1. Add command parser helpers.
2. Add schema validators.
3. Add exact world validators.
4. Replace threshold-based mode switch with command-driven transitions.
5. Add persistent mode/request state.
6. Add rejection/done/give-up handlers.
7. Inject event payload summaries into next orchestrator context.
8. Keep existing screenshot/video flow unchanged.

## `fle/agents/gym_agent.py`
1. Maintain removal of `### Entities` observation guidance.
2. Keep all other base instruction content unchanged.

## Optional `viewer.py`
1. Only if needed: surface mode-event timeline for easier inspection.

## 7. Test Plan

## 7.1 Unit-Level (if added)
1. Parser:
- valid request/done/giveup lines
- malformed JSON
- non-command first line
2. Schema validator:
- missing required keys
- enum violations
- module-type missing fields
3. Transition logic:
- request accepted path
- rejected path
- done/giveup with wrong request_id

## 7.2 Integration Run
Run a short 4-step scenario on reserved port:
1. Confirm orchestrator mode prompt on step 1.
2. Emit valid `BUILD_MODE_REQUEST` on step N.
3. Confirm next step prompt is build mode.
4. Emit DONE or GIVE_UP.
5. Confirm return to orchestrator.
6. Confirm screenshots/video still generated.

## 7.3 Validation Commands
1. `python -m py_compile run_with_video.py fle/agents/gym_agent.py`
2. `bash -n run_video_reliable.sh`
3. Viewer API checks:
- `/api/run/<v>/prompt/<step>` for mode blocks
- `/api/run/<v>/steps` for run depth

## 8. Acceptance Gates
All must pass:
1. Command-based switching works (threshold not authoritative).
2. Strict exact-coordinate precheck blocks invalid requests.
3. Build prompt is scoped and excludes module registry block.
4. DONE/GIVE_UP return transitions work with request_id matching.
5. Mode events are logged with payloads.
6. End-to-end run still outputs screenshots + MP4.

## 9. Rollback / Safety
1. Keep changes isolated to prompt/transition logic.
2. If build mode path fails in production run:
- force `FLE_PROMPT_MODE=orchestrator`
- disable command-triggered transitions via feature flag (if added)
3. Do not change rendering backend or container selection logic in this workstream.

## 10. Risks and Mitigations
1. Risk: false negatives in strict line checks.
- Mitigation: explicit rejection errors and orchestrator correction loop.
2. Risk: command syntax drift by model.
- Mitigation: strict parser + examples in orchestrator overlay.
3. Risk: mode desync on runtime errors.
- Mitigation: persistent `active_build_request` state and request_id matching.

## 11. Operator Notes
1. Keep world profile and reserved port policy unchanged.
2. Continue benchmark screenshot backend policy unchanged.
3. Validate with short runs before full 30-step runs.

