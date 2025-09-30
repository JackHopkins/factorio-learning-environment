"""
End-to-end pipeline for replay → cinematics.

This mirrors `run_to_mp4.py` but replaces "take screenshots after each
program" logic with event-driven shot generation via the Cinematographer.

Usage (CLI):

    python -m fle.eval.analysis.runtime_to_cinema VERSION --output-dir vids

It will:
    1. Fetch programs for the requested version from Postgres.
    2. Replay them in a gym environment.
    3. Feed action/world deltas into `Cinematographer.observe`.
    4. Submit the resulting plan to the admin Cutscene tool.
    5. Optionally wait for completion and fetch the shot report.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
from dotenv import load_dotenv

from fle.env import FactorioInstance
from fle.env.tools.admin.cutscene.client import Cutscene
from fle.eval.analysis.cinematographer import CameraPrefs, Cinematographer, GameClock
from fle.eval.analysis.ast_actions import parse_actions
from fle.commons.models.program import Program
from fle.eval.tasks.task_factory import TaskFactory


load_dotenv()


# --- DB helpers ------------------------------------------------------------


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("SKILLS_DB_HOST"),
        port=os.getenv("SKILLS_DB_PORT"),
        dbname=os.getenv("SKILLS_DB_NAME"),
        user=os.getenv("SKILLS_DB_USER"),
        password=os.getenv("SKILLS_DB_PASSWORD"),
    )


def get_program_chain(conn, version: int) -> List[tuple[int, Any]]:
    query = """
        SELECT id, created_at FROM programs
        WHERE version = %s
        AND state_json IS NOT NULL
        ORDER BY created_at ASC
        LIMIT 3000
    """
    with conn.cursor() as cur:
        cur.execute(query, (version,))
        return cur.fetchall()


def get_program_state(conn, program_id: int) -> Optional[Program]:
    query = "SELECT * FROM programs WHERE id = %s"
    with conn.cursor() as cur:
        cur.execute(query, (program_id,))
        row = cur.fetchone()
        if not row:
            return None
        col_names = [desc[0] for desc in cur.description]
        return Program.from_row(dict(zip(col_names, row)))


# --- Environment / Replay -------------------------------------------------


def create_instance_and_task(
    version: int, address: str, tcp_port: int
) -> tuple[FactorioInstance, Any]:
    conn = get_db_connection()
    try:
        query = """
            SELECT meta FROM programs
            WHERE version = %s
            AND meta IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
        """
        with conn.cursor() as cur:
            cur.execute(query, (version,))
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No programs found for version {version}")

            meta = result[0]
            description = meta.get("version_description", "")
            task_key = None
            if "type:" in description:
                task_key = description.split("type:")[1].split("\n")[0].strip()

            task = TaskFactory.create_task(task_key or "iron_plate_throughput")

            instance = FactorioInstance(
                address=address,
                tcp_port=tcp_port,
                fast=True,
                cache_scripts=True,
                peaceful=True,
            )
            instance.set_speed_and_unpause(1.0)
            task.setup(instance)
            return instance, task
    finally:
        conn.close()


# --- Cinematography -------------------------------------------------------


def parse_program_actions(code: str) -> List[Dict[str, Any]]:
    """Parse a program's code to extract Factorio actions using AST.

    Returns:
        List of action dictionaries with type, args, and line_no.
    """
    action_sites = parse_actions(code)

    # Convert ActionSite objects to the expected dictionary format
    actions = []
    for site in action_sites:
        action_dict = {
            "type": site.type,
            "args": site.args,
            "line_no": site.line_no,
        }
        actions.append(action_dict)

    return actions


def generate_runtime_shot_code(
    action_type: str, action_data: dict, shot_id: str
) -> str:
    """Generate runtime code to capture positions and create shots dynamically."""

    if action_type == "move_to":
        # For movement, implement buffering to avoid excessive camera transitions
        return f'''
# CINEMA: Movement buffering for {shot_id}
if not hasattr(namespace, '_cinema_last_pos'):
    namespace._cinema_last_pos = None
    namespace._cinema_movement_buffer = []

current_pos = namespace.player_location
current_tick = get_elapsed_ticks()

# Calculate distance from last recorded position
if namespace._cinema_last_pos:
    distance = ((current_pos.x - namespace._cinema_last_pos.x) ** 2 + 
                (current_pos.y - namespace._cinema_last_pos.y) ** 2) ** 0.5
else:
    distance = 0

# Only create movement shots for significant movements (>15 tiles)
if distance >= 15:
    print(f"CINEMA: Significant movement detected: {{distance:.1f}} tiles")
    
    # Add to movement buffer
    namespace._cinema_movement_buffer.append({{
        "position": [current_pos.x, current_pos.y],
        "tick": current_tick,
        "distance": distance
    }})
    
    # Keep only last 3 movements in buffer
    if len(namespace._cinema_movement_buffer) > 3:
        namespace._cinema_movement_buffer.pop(0)
    
    # Create movement shot with buffered data
    if len(namespace._cinema_movement_buffer) >= 2:
        start_pos = namespace._cinema_movement_buffer[0]["position"]
        end_pos = namespace._cinema_movement_buffer[-1]["position"]
        
        # Calculate bounding box for the movement path
        min_x = min(pos["position"][0] for pos in namespace._cinema_movement_buffer)
        max_x = max(pos["position"][0] for pos in namespace._cinema_movement_buffer)
        min_y = min(pos["position"][1] for pos in namespace._cinema_movement_buffer)
        max_y = max(pos["position"][1] for pos in namespace._cinema_movement_buffer)
        
        # Add padding
        padding = 20
        movement_bbox = [
            [min_x - padding, min_y - padding],
            [max_x + padding, max_y + padding]
        ]
        
        cinema_shot = {{
            "id": "{shot_id}",
            "type": "player_movement", 
            "position": [current_pos.x, current_pos.y],
            "start_position": start_pos,
            "end_position": end_pos,
            "movement_bbox": movement_bbox,
            "total_distance": sum(pos["distance"] for pos in namespace._cinema_movement_buffer),
            "timestamp": current_tick
        }}
        print(f"CINEMA: Generated buffered movement shot: {{cinema_shot}}")
    
    # Update last position
    namespace._cinema_last_pos = current_pos
else:
    print(f"CINEMA: Small movement ignored: {{distance:.1f}} tiles")
'''

    elif action_type == "place_entity":
        # For entity placement, capture the entity position after placement
        return f'''
# CINEMA: Entity placement shot for {shot_id}
# Get the most recently placed entity of this type
recent_entities = get_entities(position=namespace.player_location, radius=20)
if recent_entities:
    latest_entity = max(recent_entities, key=lambda e: getattr(e, 'tick', 0))
    entity_pos = [latest_entity.position.x, latest_entity.position.y]
    print(f"CINEMA: Entity placed at {{entity_pos}}")
    cinema_shot = {{
        "id": "{shot_id}",
        "type": "entity_placed",
        "position": entity_pos,
        "entity_type": latest_entity.name,
        "timestamp": get_elapsed_ticks()
    }}
    print(f"CINEMA: Generated placement shot: {{cinema_shot}}")
'''

    elif action_type == "connect_entities":
        # For connections, we need to extract the entity variables from the function call
        # This will be handled by the splicing logic that parses the actual function call
        return f"""
# CINEMA: Connection shot will be generated by parsing the actual connect_entities call
# This placeholder will be replaced with actual entity-specific code
print(f"CINEMA: Placeholder for connect_entities shot {shot_id}")
"""

    return ""


def generate_connect_entities_cinema_code(action_data: dict, shot_id: str) -> str:
    """Generate cinema code for connect_entities using AST-parsed action data."""

    # Extract entity expressions and prototype from the action data
    a_expr = action_data.get("a_expr", "entity1")
    b_expr = action_data.get("b_expr", "entity2")
    prototype_name = action_data.get("proto_name", "Unknown")

    return f'''
# CINEMA: Connection shot for {shot_id}
# Focus on the two entities being connected: {a_expr} and {b_expr}
try:
    entity1 = {a_expr}
    entity2 = {b_expr}
    
    if hasattr(entity1, 'position') and hasattr(entity2, 'position'):
        pos1 = [entity1.position.x, entity1.position.y]
        pos2 = [entity2.position.x, entity2.position.y]
        
        # Calculate bounding box to encompass both entities
        min_x = min(pos1[0], pos2[0])
        max_x = max(pos1[0], pos2[0])
        min_y = min(pos1[1], pos2[1])
        max_y = max(pos1[1], pos2[1])
        
        # Add padding for better framing
        padding = 20
        connection_bbox = [
            [min_x - padding, min_y - padding],
            [max_x + padding, max_y + padding]
        ]
        
        print(f"CINEMA: Connecting {{entity1.name}} to {{entity2.name}} with {prototype_name}")
        
        # Create connection shot: zoom out to show both entities
        connection_shot = {{
            "id": "{shot_id}",
            "type": "zoom_to_fit",
            "bbox": connection_bbox,
            "zoom": 0.7,  # Zoom out to show both entities
            "pan_ms": 1500,
            "dwell_ms": 2000,
            "timestamp": get_elapsed_ticks()
        }}
        print(f"CINEMA: Generated connection shot: {{connection_shot}}")
    else:
        print(f"CINEMA: Entities {a_expr} or {b_expr} don't have position attributes")
except Exception as e:
    print(f"CINEMA: Error generating connection shot: {{e}}")
'''


def splice_cinema_code(original_code: str, actions: list) -> str:
    """Splice cinema code between actions in the original program."""
    lines = original_code.split("\n")
    new_lines = []

    action_index = 0

    for i, line in enumerate(lines):
        # Check if this line contains an action we want to capture
        if action_index < len(actions):
            action = actions[action_index]

            # Look for the action in this line
            if (
                (action["type"] == "move_to" and "move_to(" in line)
                or (action["type"] == "place_entity" and "place_entity(" in line)
                or (
                    action["type"] == "connect_entities" and "connect_entities(" in line
                )
            ):
                # Generate shot ID
                shot_id = f"{action['type']}_{i}_{action_index}"

                # For connect_entities, use the AST-parsed action data
                if action["type"] == "connect_entities":
                    cinema_code = generate_connect_entities_cinema_code(
                        action["args"], shot_id
                    )
                    if cinema_code.strip():
                        new_lines.append(cinema_code)
                else:
                    # Generate runtime cinema code for other actions
                    cinema_code = generate_runtime_shot_code(
                        action["type"], action, shot_id
                    )

                # Add the actual action line
                new_lines.append(line)

                # For move_to and place_entity, add cinema code AFTER the action
                if (
                    action["type"] in ["move_to", "place_entity"]
                    and cinema_code.strip()
                ):
                    new_lines.append(cinema_code)

                action_index += 1
            else:
                # Regular line, add as-is
                new_lines.append(line)
        else:
            # No more actions to process, add line as-is
            new_lines.append(line)

    return "\n".join(new_lines)


def detect_game_events(
    instance: FactorioInstance,
    program: Any,
    response: tuple,
    previous_state: Dict[str, Any],
) -> List[tuple[str, Dict[str, Any]]]:
    """Detect game events by analyzing program actions and game state changes.

    Returns:
        List of (event_type, delta) tuples for multiple detected events.
    """
    current_tick = instance.get_elapsed_ticks()
    namespace_pos = (
        instance.namespace.player_location if hasattr(instance, "namespace") else None
    )
    pos = (
        [namespace_pos.x, namespace_pos.y]
        if namespace_pos and hasattr(namespace_pos, "x")
        else [0, 0]
    )

    events = []
    seen_events = set()  # Track seen events to prevent duplicates

    # Parse actions from the program code (just to identify what actions exist)
    actions = parse_program_actions(program.code) if program and program.code else []

    # Get current game state
    current_state = {
        "tick": current_tick,
        "position": pos,
        "prints": response[1] or "",
        "errors": response[2] or "",
        "actions": actions,
    }

    # 1. DETECT MOVEMENT EVENTS based on actual position changes
    if previous_state and "position" in previous_state:
        prev_pos = previous_state["position"]
        distance = ((pos[0] - prev_pos[0]) ** 2 + (pos[1] - prev_pos[1]) ** 2) ** 0.5

        # Only create significant movement events (more than 10 tiles)
        if distance >= 10:
            event_type = "player_movement"
            delta = {
                "position": pos,
                "movement_distance": distance,
                "from_position": prev_pos,
                "to_position": pos,
            }

            # Create a bounding box around the movement path
            center_x = (pos[0] + prev_pos[0]) / 2
            center_y = (pos[1] + prev_pos[1]) / 2
            padding = max(distance / 2, 15)  # Dynamic padding based on distance

            delta["movement_bbox"] = [
                [center_x - padding, center_y - padding],
                [center_x + padding, center_y + padding],
            ]
            delta["movement_center"] = [center_x, center_y]

            event_key = f"player_movement_{current_tick}_{pos}"
            if event_key not in seen_events:
                seen_events.add(event_key)
                events.append((event_type, delta))

    # 2. DETECT CONNECT_ENTITIES EVENTS based on action detection + game state
    has_connect_actions = any(
        action["type"] == "connect_entities" for action in actions
    )
    if has_connect_actions:
        event_type = "infrastructure_connection"
        delta = {"position": pos}

        # Try to get entities around the player position to find what was connected
        try:
            # Get entities in a reasonable radius around the player
            entities = instance.first_namespace.get_entities(
                position=pos,
                radius=50,  # Look in a 50-tile radius
                limit=100,
            )

            if entities and len(entities) >= 2:
                # Find the most recent entities (assuming they were just placed)
                recent_entities = sorted(
                    entities, key=lambda e: getattr(e, "tick", 0), reverse=True
                )[:2]

                if len(recent_entities) >= 2:
                    # Calculate bounding box that encompasses both entities with padding
                    positions = []
                    for entity in recent_entities:
                        if hasattr(entity, "position"):
                            positions.append([entity.position.x, entity.position.y])

                    if len(positions) >= 2:
                        # Calculate min/max coordinates
                        min_x = min(pos[0] for pos in positions)
                        max_x = max(pos[0] for pos in positions)
                        min_y = min(pos[1] for pos in positions)
                        max_y = max(pos[1] for pos in positions)

                        # Add padding (20 tiles)
                        padding = 20
                        delta["connection_bbox"] = [
                            [min_x - padding, min_y - padding],
                            [max_x + padding, max_y + padding],
                        ]
                        delta["center_position"] = [
                            (min_x + max_x) / 2,
                            (min_y + max_y) / 2,
                        ]
                        delta["entity_count"] = len(recent_entities)

                        # Determine connection type based on entity types
                        entity_types = [getattr(e, "name", "") for e in recent_entities]
                        if any("belt" in et for et in entity_types):
                            event_type = "belt_connection"
                        elif any("pole" in et for et in entity_types):
                            event_type = "power_connection"
                        elif any("pipe" in et for et in entity_types):
                            event_type = "fluid_connection"
                        else:
                            event_type = "infrastructure_connection"

            # Fallback to player position if we can't find entities
            if "connection_bbox" not in delta:
                delta["factory_bbox"] = [
                    [pos[0] - 30, pos[1] - 30],
                    [pos[0] + 30, pos[1] + 30],
                ]

        except Exception:
            # Fallback if entity detection fails
            delta["factory_bbox"] = [
                [pos[0] - 30, pos[1] - 30],
                [pos[0] + 30, pos[1] + 30],
            ]

        event_key = f"{event_type}_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append((event_type, delta))

    # 3. DETECT PLACE_ENTITY EVENTS based on action detection + game state
    for action in actions:
        if action["type"] == "place_entity":
            entity_type = action.get("args", {}).get("prototype") or ""
            entity_type = entity_type.lower() if entity_type else ""

            # Only create events if we have a valid entity type
            if entity_type:
                event_type = None
                delta = {"position": pos, "entity_type": entity_type}

                # Classify entity placements
                if entity_type in [
                    "boiler",
                    "steam_engine",
                    "offshorepump",
                    "offshore_pump",
                ]:
                    event_type = "power_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 15, pos[1] - 15],
                        [pos[0] + 15, pos[1] + 15],
                    ]
                elif entity_type in [
                    "burner_mining_drill",
                    "electric_mining_drill",
                    "burnerminingdrill",
                    "electricminingdrill",
                ]:
                    event_type = "mining_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 10, pos[1] - 10],
                        [pos[0] + 10, pos[1] + 10],
                    ]
                elif entity_type in [
                    "stone_furnace",
                    "steel_furnace",
                    "electric_furnace",
                    "stonefurnace",
                    "steelfurnace",
                    "electricfurnace",
                ]:
                    event_type = "smelting_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 8, pos[1] - 8],
                        [pos[0] + 8, pos[1] + 8],
                    ]
                elif entity_type in [
                    "assembly_machine_1",
                    "assembly_machine_2",
                    "assembly_machine_3",
                    "assemblymachine1",
                    "assemblymachine2",
                    "assemblymachine3",
                ]:
                    event_type = "assembly_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 12, pos[1] - 12],
                        [pos[0] + 12, pos[1] + 12],
                    ]
                elif entity_type in ["lab"]:
                    event_type = "research_setup"
                    delta["factory_bbox"] = [
                        [pos[0] - 8, pos[1] - 8],
                        [pos[0] + 8, pos[1] + 8],
                    ]
                else:
                    event_type = "building_placed"
                    delta["factory_bbox"] = [
                        [pos[0] - 5, pos[1] - 5],
                        [pos[0] + 5, pos[1] + 5],
                    ]

                if event_type:
                    event_key = f"{event_type}_{current_tick}_{entity_type}_{pos}"
                    if event_key not in seen_events:
                        seen_events.add(event_key)
                        events.append((event_type, delta))

    # Also check for events based on game output
    prints_lower = current_state["prints"].lower()

    # Check for fuel inserter events
    if "inserter" in prints_lower and "fuel" in prints_lower:
        event_key = f"fuel_inserter_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append(("fuel_inserter", {"position": pos}))

    # Check for power/electricity events
    if any(
        keyword in prints_lower for keyword in ["power", "electric", "steam", "boiler"]
    ):
        if any(
            keyword in prints_lower for keyword in ["online", "connected", "working"]
        ):
            event_key = f"power_online_{current_tick}_{pos}"
            if event_key not in seen_events:
                seen_events.add(event_key)
                events.append(
                    (
                        "power_online",
                        {
                            "position": pos,
                            "factory_bbox": [
                                [pos[0] - 25, pos[1] - 25],
                                [pos[0] + 25, pos[1] + 25],
                            ],
                        },
                    )
                )

    # Check for production/completion events
    if any(
        keyword in prints_lower for keyword in ["completed", "finished", "production"]
    ):
        event_key = f"production_milestone_{current_tick}_{pos}"
        if event_key not in seen_events:
            seen_events.add(event_key)
            events.append(
                (
                    "production_milestone",
                    {
                        "position": pos,
                        "factory_bbox": [
                            [pos[0] - 30, pos[1] - 30],
                            [pos[0] + 30, pos[1] + 30],
                        ],
                    },
                )
            )

    return events


def process_programs(
    version: int,
    cin: Cinematographer,
    instance: FactorioInstance,
    programs: Iterable[tuple[int, Any]],
    conn,
    max_steps: int,
) -> Dict[str, Any]:
    cutscene_tool = Cutscene(instance.lua_script_manager, instance.first_namespace)

    print(
        f"Processing version {version} with {len(list(programs))} programs (max {max_steps} steps)"
    )
    programs = list(programs)  # Convert back to list after len() call

    instance.reset()
    print("Environment reset complete")

    screenshot_sequences: List[Dict[str, Any]] = []

    # Track game state for event detection
    previous_state = None
    active_cutscene_plans: List[str] = []
    total_events_detected = 0

    for idx, (program_id, created_at) in enumerate(programs):
        if idx >= max_steps:
            print(f"Reached maximum steps limit ({max_steps}), stopping")
            break

        print(f"\n--- Processing program {idx + 1}/{len(programs)}: {program_id} ---")

        program = get_program_state(conn, program_id)
        if not program or not program.code:
            print(f"Skipping program {program_id} - no code available")
            continue

        print(f"Code preview: {program.code[:100]}...")

        if program.state:
            print("Resetting environment with program state")
            instance.reset(program.state)

        # Parse actions and splice cinema code
        actions = parse_program_actions(program.code) if program.code else []
        cinema_code = splice_cinema_code(program.code, actions)

        print("Executing program with cinema code...")
        print(f"Original code length: {len(program.code)}")
        print(f"Cinema-spliced code length: {len(cinema_code)}")

        response = instance.eval(cinema_code)

        # Log execution results
        if response[2]:  # errors
            print(f"Execution errors: {response[2]}")
        if response[1]:  # prints
            print(f"Program output: {response[1]}")

        screenshot_sequences.append(
            {
                "program_id": program_id,
                "code": program.code,
                "cinema_code": cinema_code,
                "actions": actions,
                "prints": response[1],
                "errors": response[2],
                "created_at": str(created_at),
            }
        )

        # Detect multiple game events from this program execution
        events = detect_game_events(instance, program, response, previous_state)

        current_tick = instance.get_elapsed_ticks()
        namespace_pos = (
            instance.namespace.player_location
            if hasattr(instance, "namespace")
            else None
        )
        pos = (
            [namespace_pos.x, namespace_pos.y]
            if namespace_pos and hasattr(namespace_pos, "x")
            else [0, 0]
        )

        print(f"Current game state: tick={current_tick}, position={pos}")
        print(f"Detected {len(events)} events from program execution")

        # Process each detected event
        for event_type, delta in events:
            total_events_detected += 1
            event = {
                "tick": current_tick,
                "event": event_type,
                "position": delta.get("position", pos),
            }

            # Observe the event with cinematographer
            cin.observe(event, delta)

            print(
                f"  Event {total_events_detected}: '{event_type}' at {event['position']}"
            )
            if delta.get("factory_bbox"):
                print(f"    Factory bbox: {delta['factory_bbox']}")
            if delta.get("entity_type"):
                print(f"    Entity type: {delta['entity_type']}")

        # Update previous state for next iteration
        previous_state = {
            "tick": current_tick,
            "position": pos,
            "prints": response[1] or "",
        }

        # Create individual cutscene shots for each significant event immediately
        for event_type, delta in events:
            if event_type in [
                "power_setup",
                "mining_setup",
                "smelting_setup",
                "assembly_setup",
                "research_setup",
                "belt_connection",
                "power_connection",
                "fluid_connection",
                "infrastructure_connection",
                "player_movement",
            ]:
                # Create an immediate cutscene shot for this event
                event_pos = delta.get("position", pos)
                factory_bbox = delta.get("factory_bbox")
                connection_bbox = delta.get("connection_bbox")
                movement_bbox = delta.get("movement_bbox")

                # Create a single-shot plan for immediate execution
                shot_kind = {}
                # Priority: connection_bbox > movement_bbox > factory_bbox > focus position
                if connection_bbox:
                    shot_kind = {"type": "zoom_to_fit", "bbox": connection_bbox}
                elif movement_bbox:
                    shot_kind = {"type": "zoom_to_fit", "bbox": movement_bbox}
                elif factory_bbox:
                    shot_kind = {"type": "zoom_to_fit", "bbox": factory_bbox}
                else:
                    shot_kind = {"type": "focus_position", "pos": event_pos}

                immediate_plan = {
                    "player": 1,
                    "start_zoom": 1.0,
                    "shots": [
                        {
                            "id": f"{event_type}-{current_tick}",
                            "pri": 10,
                            "when": {"start_tick": 0},  # Start immediately
                            "kind": shot_kind,
                            "pan_ms": 1500,
                            "dwell_ms": 2000,
                            "zoom": (
                                0.8
                                if event_type
                                in [
                                    "belt_connection",
                                    "power_connection",
                                    "fluid_connection",
                                    "infrastructure_connection",
                                ]
                                else 0.9
                                if event_type == "player_movement"
                                else 1.2
                                if event_type == "power_setup"
                                else 1.5
                            ),
                            "tags": [event_type],
                        }
                    ],
                }

                print(f"\nCreating immediate cutscene for {event_type} at {event_pos}")

                queue_response = cutscene_tool.queue_plan(immediate_plan)
                print(
                    f"Queue response type: {type(queue_response)}, value: {queue_response}"
                )

                if isinstance(queue_response, dict) and queue_response.get("ok"):
                    plan_id = queue_response.get("plan_id")

                    # Start the plan immediately
                    start_response = cutscene_tool.start_plan(plan_id, 1)
                    if start_response.get("ok"):
                        print(
                            f"Started immediate cutscene '{plan_id}' for {event_type}"
                        )
                        active_cutscene_plans.append(plan_id)

                        # Wait for the cutscene to complete
                        import time

                        time.sleep(3.5)  # Wait for pan + dwell time

                        # Check if cutscene finished
                        status_response = cutscene_tool.fetch_report(plan_id, 1)
                        if status_response.get("ok"):
                            report = status_response.get("report", {})
                            print(f"Cutscene status: {report.get('state', 'unknown')}")
                    else:
                        print(f"Failed to start immediate cutscene: {start_response}")
                else:
                    print(f"Failed to queue immediate cutscene: {queue_response}")

    # Create a final comprehensive plan with all remaining events
    final_plan = cin.build_plan(player=1)

    # If no shots were generated, create a default overview plan
    if not final_plan["shots"]:
        print("\nNo shots generated from events, creating default overview plan...")
        player_pos = getattr(instance, "namespace", None)
        if player_pos and hasattr(player_pos, "player_location"):
            location = player_pos.player_location
            pos = [location.x, location.y]
        else:
            pos = [0, 0]

        final_plan = {
            "player": 1,
            "start_zoom": 1.0,
            "shots": [
                {
                    "id": "intro-overview",
                    "pri": 10,
                    "when": {"start_tick": 0},
                    "kind": {
                        "type": "focus_position",
                        "pos": [pos[0] - 30, pos[1] - 20],
                    },
                    "pan_ms": 2500,
                    "dwell_ms": 1000,
                    "zoom": 0.8,
                },
                {
                    "id": "factory-center",
                    "pri": 9,
                    "when": {"start_tick": 3500},
                    "kind": {"type": "focus_position", "pos": pos},
                    "pan_ms": 2000,
                    "dwell_ms": 1500,
                    "zoom": 1.0,
                },
                {
                    "id": "close-up",
                    "pri": 8,
                    "when": {"start_tick": 7000},
                    "kind": {
                        "type": "focus_position",
                        "pos": [pos[0] + 10, pos[1] + 10],
                    },
                    "pan_ms": 1500,
                    "dwell_ms": 2000,
                    "zoom": 1.5,
                },
            ],
        }

    print(f"\nFinal plan contains {len(final_plan['shots'])} shots")

    # Queue and start the final plan
    final_response = cutscene_tool.queue_plan(final_plan)
    print(f"Final response type: {type(final_response)}, value: {final_response}")

    if not isinstance(final_response, dict) or not final_response.get("ok"):
        print(f"Warning: Failed to queue final plan: {final_response}")
    else:
        final_plan_id = final_response.get("plan_id")
        print(f"Queued final plan '{final_plan_id}'")

        # Start the final plan
        start_response = cutscene_tool.start_plan(final_plan_id, 1)
        if start_response.get("ok"):
            print(f"Started final cutscene plan '{final_plan_id}'")
        else:
            print(f"Failed to start final cutscene plan: {start_response}")

    print("\nProcessing complete:")
    print(f"  - Total programs processed: {min(len(programs), max_steps)}")
    print(f"  - Total events detected: {total_events_detected}")
    print(f"  - Active cutscene plans: {len(active_cutscene_plans)}")
    print(f"  - Final plan shots: {len(final_plan['shots'])}")

    return {
        "plan": final_plan,
        "enqueue": final_response,
        "programs": screenshot_sequences,
        "stats": {
            "programs_processed": min(len(programs), max_steps),
            "events_detected": total_events_detected,
            "cutscene_plans": active_cutscene_plans,
        },
    }


# --- CLI -----------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Replay programs with cinematics")
    parser.add_argument("versions", nargs="+", type=int)
    parser.add_argument("--output-dir", "-o", default="cinema_runs")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument(
        "--address", default=os.getenv("FACTORIO_SERVER_ADDRESS", "localhost")
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=int(os.getenv("FACTORIO_SERVER_PORT", "27000")),
    )
    args = parser.parse_args()

    output_base = Path(args.output_dir)
    output_base.mkdir(parents=True, exist_ok=True)

    conn = get_db_connection()
    try:
        for version in args.versions:
            programs = get_program_chain(conn, version)
            if not programs:
                print(f"No programs for version {version}")
                continue

            instance, task = create_instance_and_task(
                version, args.address, args.tcp_port
            )
            instance.set_speed_and_unpause(1.0)
            cin = Cinematographer(CameraPrefs(), GameClock())
            report = process_programs(
                version, cin, instance, programs, conn, args.max_steps
            )

            out_dir = output_base / str(version)
            out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "plan.json").open("w", encoding="utf-8") as fh:
            json.dump(report["plan"], fh, indent=2)
        with (out_dir / "enqueue.json").open("w", encoding="utf-8") as fh:
            json.dump(report["enqueue"], fh, indent=2)
        with (out_dir / "programs.json").open("w", encoding="utf-8") as fh:
            json.dump(report["programs"], fh, indent=2)

            print(f"Version {version}: plan written to {out_dir}")
            instance.cleanup()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
