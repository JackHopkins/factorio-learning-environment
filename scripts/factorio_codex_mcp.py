"""Minimal stdio MCP server exposing Factorio envd tools to Codex.

Newline-delimited JSON-RPC 2.0 (current MCP stdio transport), no third-party
dependencies. The lease is created by the outer harness runner; this process
only observes/executes against ENVD_URL for LEASE_ID.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fle.envd.knowledge import ApiReference, GameDataReference, load_game_data

# Keep the adapter on the current MCP revision while accepting the revisions
# used by existing Codex/Hermes/OpenCode installations.  The adapter only uses
# the stable initialize/tools surface shared by these revisions.
PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
REPEATED_FAILURE_LIMIT = 3
MAX_TOOL_RESULT_CHARS = 60_000
# These limits apply only to the model-facing MCP projection.  The envd
# response and the terminal signal remain complete for privileged accounting.
MAX_MODEL_EVENT_ITEMS = 48
MAX_MODEL_CRAFT_ITEMS = 16
MAX_MODEL_EVENT_TEXT_CHARS = 8_000
MAX_MODEL_NESTED_ITEMS = 48
MAX_MODEL_NESTED_STRING_CHARS = 4_000

_TERMINAL_EVENT_KINDS = frozenset(
    {
        "contract_fulfilled",
        "contract_expired",
        "termination_classified",
        "verification_completed",
        "character_died",
    }
)

_last_failure_fingerprint: str | None = None
_consecutive_failure_count = 0
_process_nonce = hashlib.sha256(
    f"{os.getpid()}:{time.time_ns()}".encode("utf-8")
).hexdigest()[:16]
_tool_call_sequence = 0
_api_reference: ApiReference | None = None
_game_data_reference: GameDataReference | None = None
_game_data_source: str | None = None


def _reset_repetition_state() -> None:
    global _last_failure_fingerprint, _consecutive_failure_count
    _last_failure_fingerprint = None
    _consecutive_failure_count = 0


def _knowledge() -> tuple[ApiReference, GameDataReference]:
    """Load the immutable references once per MCP process."""

    global _api_reference, _game_data_reference, _game_data_source
    if _api_reference is None:
        _api_reference = ApiReference()
    configured = os.environ.get("FACTORIO_GAME_DATA_FILE") or None
    if _game_data_reference is None or configured != _game_data_source:
        _game_data_reference, _game_data_source = load_game_data(configured)
    return _api_reference, _game_data_reference


def _memory_enabled() -> bool:
    return os.environ.get("MEMORY_ENABLED", "0").lower() in {"1", "true", "yes"}


def _query_path(path: str, values: dict[str, object]) -> str:
    encoded = urllib.parse.urlencode(
        [(key, str(value)) for key, value in values.items() if value is not None]
    )
    return f"{path}?{encoded}" if encoded else path


def _next_execute_request_id(jsonrpc_id: object | None) -> str:
    """Create one lease-unique key for this logical MCP invocation."""

    global _tool_call_sequence
    _tool_call_sequence += 1
    material = f"{_process_nonce}:{_tool_call_sequence}:{jsonrpc_id}"
    return "mcp:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _program_fingerprint(code: str) -> str:
    """Identify semantically identical source despite whitespace/comments."""

    try:
        normalized = ast.dump(ast.parse(code), include_attributes=False)
    except SyntaxError:
        normalized = code.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _record_execution_result(fingerprint: str, failed: bool) -> int:
    global _last_failure_fingerprint, _consecutive_failure_count
    if not failed:
        _reset_repetition_state()
        return 0
    if fingerprint == _last_failure_fingerprint:
        _consecutive_failure_count += 1
    else:
        _last_failure_fingerprint = fingerprint
        _consecutive_failure_count = 1
    return _consecutive_failure_count


def _repetition_error(count: int) -> str:
    return (
        "error: repetition circuit breaker: this normalized program has already "
        f"failed {count} consecutive times. It was not executed again and does "
        "not count as an environment intervention. Read the prior error and "
        "submit a materially different program; repeating whitespace or comment "
        "changes will remain blocked."
    )


def _envd(method: str, path: str, payload: dict | None = None) -> dict:
    url = os.environ["ENVD_URL"].rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    attempts = (
        2
        if method == "POST"
        and path.endswith("/execute")
        and payload is not None
        and payload.get("request_id")
        else 1
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                result = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            detail = body
            try:
                error_payload = json.loads(body)
                detail = str(
                    error_payload.get("detail")
                    or error_payload.get("error")
                    or error_payload
                )
            except json.JSONDecodeError:
                pass
            _trace(f"{method} {path} -> HTTP {exc.code}: {detail[:500]}")
            raise RuntimeError(f"envd HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 >= attempts:
                raise
            _trace(
                f"{method} {path} -> ambiguous transport error; "
                "retrying with the same request_id"
            )
    _trace(f"{method} {path} -> ok")
    return result


def _trace(message: str) -> None:
    """Debug trace to a fixed file so harness runs are auditable."""

    log_path = os.environ.get("MCP_TRACE_FILE")
    if not log_path:
        return
    try:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%H:%M:%S')} {message}\n")
    except OSError:
        pass


def _signal_epoch_terminal(reason: str, payload: dict) -> None:
    """Notify the outer harness that the committed order is no longer open."""

    path = os.environ.get("MCP_TERMINAL_FILE")
    if not path:
        return
    temporary = path + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump({"reason": reason, "payload": payload}, handle)
        os.replace(temporary, path)
        _trace(f"epoch terminal -> {reason}")
    except OSError as exc:
        _trace(f"epoch terminal signal failed: {exc}")


def _truncate_model_text(value: Any, max_chars: int) -> str:
    """Keep both ends of a model-facing string when it exceeds its budget."""

    text = str(value)
    if len(text) <= max_chars:
        return text
    if max_chars <= 0:
        return ""
    marker = f"\n...[truncated {len(text) - max_chars} chars]...\n"
    if len(marker) >= max_chars:
        return text[:max_chars]
    remaining = max_chars - len(marker)
    head = remaining // 2
    tail = remaining - head
    return text[:head] + marker + text[-tail:]


def _numeric_value(value: Any) -> float | None:
    """Parse the scalar numbers emitted by Lua/RCON without accepting booleans."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _normalise_number(value: float) -> int | float:
    if value.is_integer():
        return int(value)
    return round(value, 6)


def _bounded_nested_value(
    value: Any,
    *,
    max_items: int = MAX_MODEL_NESTED_ITEMS,
    max_string_chars: int = MAX_MODEL_NESTED_STRING_CHARS,
) -> Any:
    """Bound nested diagnostic values while retaining useful edge fields."""

    if isinstance(value, str):
        return _truncate_model_text(value, max_string_chars)
    if isinstance(value, dict):
        items = list(value.items())
        if len(items) <= max_items:
            return {
                str(key): _bounded_nested_value(
                    item,
                    max_items=max_items,
                    max_string_chars=max_string_chars,
                )
                for key, item in items
            }

        priority = {
            "error",
            "message",
            "reason",
            "status",
            "terminal_reason",
            "kind",
        }
        selected: list[tuple[Any, Any]] = []
        selected_keys: set[str] = set()
        for key, item in items:
            if str(key) in priority:
                selected.append((key, item))
                selected_keys.add(str(key))
        edge_count = max(max_items - len(selected), 0)
        head_count = edge_count // 2
        edge_items = [
            (key, item)
            for key, item in items
            if str(key) not in selected_keys
        ]
        selected.extend(edge_items[:head_count])
        selected_keys.update(str(key) for key, _ in edge_items[:head_count])
        tail_items = [
            (key, item)
            for key, item in edge_items[head_count:]
            if str(key) not in selected_keys
        ]
        selected.extend(tail_items[-(edge_count - head_count) :])
        result = {
            str(key): _bounded_nested_value(
                item,
                max_items=max_items,
                max_string_chars=max_string_chars,
            )
            for key, item in selected
        }
        result["_truncated_keys"] = len(items) - len(selected)
        return result
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        if len(items) <= max_items:
            return [
                _bounded_nested_value(
                    item,
                    max_items=max_items,
                    max_string_chars=max_string_chars,
                )
                for item in items
            ]
        head_count = max_items // 2
        tail_count = max_items - head_count
        return [
            *[
                _bounded_nested_value(
                    item,
                    max_items=max_items,
                    max_string_chars=max_string_chars,
                )
                for item in items[:head_count]
            ],
            {"_truncated_items": len(items) - max_items},
            *[
                _bounded_nested_value(
                    item,
                    max_items=max_items,
                    max_string_chars=max_string_chars,
                )
                for item in items[-tail_count:]
            ],
        ]
    return value


def _numeric_totals(records: list[dict[str, Any]], field: str) -> dict[str, int | float]:
    totals: dict[str, float] = {}
    for record in records:
        values = record.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            number = _numeric_value(value)
            if number is not None:
                name = str(key)
                totals[name] = totals.get(name, 0.0) + number
    return {
        key: _normalise_number(totals[key]) for key in sorted(totals)
    }


def _craft_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        # A previously projected value is already aggregate.  Do not treat its
        # summary fields as individual crafts if it is passed through again.
        if "total_operations" in value or "total_crafts" in value:
            recent = value.get("recent")
            return [item for item in (recent or []) if isinstance(item, dict)]
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, dict)]
    return []


def _aggregate_craft_history(value: Any) -> Any:
    """Replace the unbounded per-craft list with totals and a tiny recent view."""

    if isinstance(value, dict) and (
        "total_operations" in value or "total_crafts" in value
    ):
        summary = dict(value)
        recent = summary.get("recent")
        if isinstance(recent, (list, tuple)):
            summary["recent"] = [
                _bounded_nested_value(item) for item in list(recent)[-MAX_MODEL_CRAFT_ITEMS:]
            ]
            if len(recent) > MAX_MODEL_CRAFT_ITEMS:
                summary["recent_truncated"] = True
        return _bounded_nested_value(summary)

    records = _craft_records(value)
    crafts = 0.0
    for record in records:
        number = _numeric_value(record.get("crafted_count", 0))
        if number is not None:
            crafts += number
    recent_records = records[-MAX_MODEL_CRAFT_ITEMS:]
    return {
        "total_operations": len(records),
        "total_crafts": _normalise_number(crafts),
        "inputs": _numeric_totals(records, "inputs"),
        "outputs": _numeric_totals(records, "outputs"),
        "recent": [_bounded_nested_value(record) for record in recent_records],
        "recent_truncated": len(records) > len(recent_records),
    }


def _shape_production_stats(value: dict[str, Any]) -> dict[str, Any]:
    shaped = {
        str(key): _bounded_nested_value(item)
        for key, item in value.items()
        if str(key) != "crafted"
    }
    if "crafted" in value:
        shaped["crafted"] = _aggregate_craft_history(value["crafted"])
    return shaped


def _event_kind(event: Any) -> str:
    if not isinstance(event, dict):
        return "unknown"
    value = event.get("kind", event.get("type", "unknown"))
    return str(value) if value is not None else "unknown"


def _event_has_error(event: Any) -> bool:
    if not isinstance(event, dict):
        return False
    kind = _event_kind(event).lower()
    if event.get("error") is True or kind in {
        "invalid_action",
        "objective_failed",
        "constraint_failed",
    }:
        return True
    for key in ("payload", "evidence"):
        nested = event.get(key)
        if isinstance(nested, dict) and (
            nested.get("error") or nested.get("exception")
        ):
            return True
    return False


def _shape_action_event(event: dict[str, Any]) -> dict[str, Any]:
    shaped = {
        str(key): _bounded_nested_value(value)
        for key, value in event.items()
        if str(key) != "result"
    }
    if "result" in event:
        result = event["result"]
        if isinstance(result, str):
            shaped["result"] = _truncate_model_text(
                result, MAX_MODEL_EVENT_TEXT_CHARS
            )
            if len(result) > MAX_MODEL_EVENT_TEXT_CHARS:
                shaped["result_truncated"] = True
        else:
            shaped["result"] = _bounded_nested_value(result)
    return shaped


def _shape_verifier_event(event: Any) -> Any:
    if not isinstance(event, dict):
        return _bounded_nested_value(event)
    return {
        str(key): _bounded_nested_value(value)
        for key, value in event.items()
    }


def _summarise_event_stream(events: Any) -> dict[str, Any]:
    if not isinstance(events, (list, tuple)):
        return {"events": _bounded_nested_value(events)}
    raw_events = list(events)
    kind_counts: dict[str, int] = {}
    for event in raw_events:
        kind = _event_kind(event)
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    selected_indices: set[int] = set()
    for index in range(min(8, len(raw_events))):
        selected_indices.add(index)
    for index in range(max(0, len(raw_events) - 8), len(raw_events)):
        selected_indices.add(index)

    # Keep the latest representative error and each terminal kind even when a
    # long wait produced thousands of ordinary progress events.
    latest_error: int | None = None
    latest_terminal: dict[str, int] = {}
    for index, event in enumerate(raw_events):
        kind = _event_kind(event)
        if _event_has_error(event):
            latest_error = index
        if kind in _TERMINAL_EVENT_KINDS:
            latest_terminal[kind] = index
    if latest_error is not None:
        selected_indices.add(latest_error)
    selected_indices.update(latest_terminal.values())

    ordered = sorted(selected_indices)
    if len(ordered) > MAX_MODEL_EVENT_ITEMS:
        priority = set(latest_terminal.values())
        if latest_error is not None:
            priority.add(latest_error)
        kept = sorted(priority)
        for index in ordered:
            if len(kept) >= MAX_MODEL_EVENT_ITEMS:
                break
            if index not in priority:
                kept.append(index)
        ordered = sorted(set(kept))[:MAX_MODEL_EVENT_ITEMS]

    shaped_events = [_shape_verifier_event(raw_events[index]) for index in ordered]
    return {
        "events": shaped_events,
        "event_count": len(raw_events),
        "events_truncated": len(ordered) < len(raw_events),
        "events_omitted": max(len(raw_events) - len(ordered), 0),
        "event_kind_counts": _bounded_nested_value(kind_counts),
    }


def _shape_model_payload(payload: Any) -> Any:
    """Project known FLE responses before they enter an OpenCode context."""

    if not isinstance(payload, dict):
        return _bounded_nested_value(payload)
    shaped = dict(payload)
    for key in ("production", "production_stats"):
        if isinstance(shaped.get(key), dict):
            shaped[key] = _shape_production_stats(shaped[key])
    if "crafted" in shaped and isinstance(shaped.get("crafted"), (dict, list, tuple)):
        shaped = _shape_production_stats(shaped)
    if isinstance(shaped.get("event"), dict):
        shaped["event"] = _shape_action_event(shaped["event"])
    for key in ("events", "event_stream", "action_events"):
        if key in shaped:
            event_summary = _summarise_event_stream(shaped[key])
            shaped[key] = event_summary.pop("events")
            if key == "events":
                shaped.update(event_summary)
            else:
                # Keep the source field name for non-canonical streams while
                # still exposing their counts with an unambiguous prefix.
                shaped.update(
                    {f"{key}_{name}": value for name, value in event_summary.items()}
                )
    return shaped


def _preserved_payload_summary(payload: Any) -> dict[str, Any]:
    """Extract terminal/error facts for the final generic truncation envelope."""

    if not isinstance(payload, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in (
        "lease_id",
        "task_id",
        "state_hash",
        "ticks",
        "terminal_reason",
        "contract_status",
    ):
        if key in payload:
            summary[key] = _bounded_nested_value(payload[key], max_string_chars=512)
    event = payload.get("event")
    if isinstance(event, dict):
        summary["event"] = {
            "error": bool(event.get("error")),
            "ticks": event.get("ticks"),
            "result": _truncate_model_text(event.get("result", ""), 128),
        }
    events = payload.get("events")
    if isinstance(events, (list, tuple)):
        event_summary = _summarise_event_stream(events)
        summary.update(
            {
                "event_count": event_summary.get("event_count", len(events)),
                "event_kind_counts": event_summary.get("event_kind_counts", {}),
                "events_omitted": event_summary.get("events_omitted", 0),
            }
        )
    production = payload.get("production") or payload.get("production_stats")
    if isinstance(production, dict) and "crafted" in production:
        crafted = _aggregate_craft_history(production["crafted"])
        if isinstance(crafted, dict):
            summary["crafted"] = {
                key: crafted[key]
                for key in ("total_operations", "total_crafts", "inputs", "outputs")
                if key in crafted
            }
    return _bounded_nested_value(
        summary,
        max_items=16,
        max_string_chars=256,
    )


def _bounded_json_text(payload: dict, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Serialize a bounded model projection without hiding terminal/error facts."""

    # Keep the complete serialization only long enough to provide an audit
    # digest.  Known high-cardinality fields are removed before the normal
    # response is serialized, so craft/event history cannot fill the context.
    original = json.dumps(payload, default=str, separators=(",", ":"))
    model_payload = _shape_model_payload(payload)
    serialized = json.dumps(model_payload, default=str, separators=(",", ":"))
    if len(serialized) <= max_chars:
        return serialized

    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()
    summary = _preserved_payload_summary(payload)

    def envelope(prefix_chars: int, include_summary: bool = True) -> str:
        value: dict[str, Any] = {
            "truncated": True,
            "original_json_chars": len(original),
            "original_json_sha256": digest,
        }
        if include_summary and summary:
            value["summary"] = summary
        value["json_prefix"] = serialized[:prefix_chars]
        return json.dumps(value, separators=(",", ":"), default=str)

    # A tiny caller-supplied budget may not fit all metadata.  Prefer a valid
    # minimal JSON response over returning an over-budget or malformed prefix.
    minimal = json.dumps(
        {
            "truncated": True,
            "original_json_chars": len(original),
            "original_json_sha256": digest,
        },
        separators=(",", ":"),
    )
    if len(minimal) > max_chars:
        return json.dumps({"truncated": True}, separators=(",", ":"))

    low, high = 0, min(len(serialized), max_chars)
    best = envelope(0)
    if len(best) > max_chars:
        best = minimal
    while low <= high:
        midpoint = (low + high) // 2
        candidate = envelope(midpoint)
        if len(candidate) <= max_chars:
            best = candidate
            low = midpoint + 1
        else:
            high = midpoint - 1
    return best


TOOLS = [
    {
        "name": "factorio_observe_factory",
        "description": (
            "Direct read of the current Factorio factory state: inventory, "
            "production statistics, open customer contracts with fulfilled and "
            "remaining quantities and authoritative completion_ratio (windowed "
            "for sustained orders), authoritative customer_depots with exact "
            "sink positions, blueprint library, ticks, and state hash. Safe to "
            "request concurrently with other "
            "calls; envd still serializes operations for one lease."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cursor": {
                    "type": "string",
                    "description": "Opaque cursor returned by the previous observation.",
                },
                "keyframe": {
                    "type": "boolean",
                    "description": "Request a fresh absolute keyframe.",
                },
            },
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "description": "The lease-bound public factory observation.",
            "additionalProperties": True,
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "factorio_execute_program",
        "description": (
            "Directly submit one short Python program inside the sandboxed "
            "Factorio REPL. The program is the programmatic composition path: "
            "its public FLE calls, loops, and conditionals run synchronously in "
            "source order and count as one environment intervention. Available "
            "names include inspect_inventory, get_entities, "
            "nearest (with a specific Resource.X or Prototype.X), move_to, "
            "harvest_resource, craft_item, place_entity, wait, "
            "place_entity_next_to, insert_item, extract_item, set_entity_recipe, "
            "connect_entities, get_resource_patch, set_research, sleep, print. "
            "When insert_item is used, the result includes a delivery_receipt "
            "stating what the customer verifier credited and what remains. "
            "Do not emit MCP/network calls from the program. One intervention "
            "per tool call; the program's printed output returns. Same-lease "
            "world operations are serialized by envd."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source for one intervention.",
                }
            },
            "required": ["code"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "description": "The auditable execution result and event stream.",
            "additionalProperties": True,
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
    {
        "name": "factorio_check_throughput",
        "description": (
            "Run a server-sized autonomous depot-throughput check for the "
            "active sustained order. Agent actions are disabled while the "
            "simulation advances for one to five minutes. Returns exact "
            "per-product depot rates and target-relative scores. The check "
            "consumes contract time and is diagnostic; continuous delivery "
            "over the full order remains the rating signal."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "description": "Intervention-free depot throughput measurement.",
            "additionalProperties": True,
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
]


def _read_only_tool(name: str, description: str, properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
        "outputSchema": {"type": "object", "additionalProperties": True},
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    }


_BASE_TOOLS = list(TOOLS)
TOOLS.extend(
    [
        _read_only_tool(
            "factorio_query_state",
            (
                "Read one bounded page of public state history. Use kind to retrieve "
                "inventory deltas, raw production samples and 5s/60s/300s rates, "
                "delivery buckets and since-contract totals, entity mutations or "
                "bounded entity details, research unlocks, current contracts and "
                "historical outcomes, or corrective error evidence. The current "
                "absolute state is included; use since_revision/changed_since and "
                "window_seconds to avoid replaying old data. This never exposes "
                "reward, audit, holdout, or verifier internals."
            ),
            {
                "kind": {
                    "type": "string",
                    "enum": [
                        "inventory",
                        "production",
                        "delivery",
                        "entities",
                        "research",
                        "contracts",
                        "errors",
                    ],
                },
                "item": {
                    "type": "string",
                    "description": "Optional item filter for production or delivery.",
                },
                "window_seconds": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 86400,
                    "description": "Optional trailing simulation-time window.",
                },
                "since_revision": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Return changes after this observation revision.",
                },
                "entity_type": {
                    "type": "string",
                    "description": "Optional prototype/type filter for entity details.",
                },
                "area": {
                    "type": "object",
                    "description": "Optional bounded area: {x, y, radius}.",
                    "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "radius": {"type": "number", "minimum": 0, "maximum": 1000},
                    },
                    "required": ["x", "y", "radius"],
                    "additionalProperties": False,
                },
                "changed_since": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Entity mutation revision floor.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 128,
                    "default": 32,
                },
            },
            ["kind"],
        ),
        _read_only_tool(
            "factorio_search_reference",
            (
                "Search the complete callable FLE API manual and the exact "
                "version-matched Factorio game-data export. Results include "
                "canonical IDs. Use kinds=['api','recipe','technology',"
                "'prototype'] to narrow results; pagination uses next_cursor."
            ),
            {
                "query": {"type": "string", "description": "Terms to search for."},
                "kinds": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["api", "recipe", "technology", "prototype"]},
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "cursor": {"type": "string"},
            },
        ),
        _read_only_tool(
            "factorio_read_reference",
            (
                "Read one bounded page of a callable reference document. API "
                "IDs are api/<path>; game-data IDs are recipe:<id>, "
                "technology:<id>, or prototype:<id>."
            ),
            {
                "document_id": {"type": "string"},
                "section": {"type": "string"},
                "cursor": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1, "maximum": 60000, "default": 12000},
            },
            ["document_id"],
        ),
        _read_only_tool(
            "factorio_get_recipe",
            "Return exact recipe facts from the run's pinned Factorio export; accepts a canonical recipe or item ID. RecipeName.X aliases are normalized (RecipeName.FillLubricantBarrel is lubricant-barrel). Product IDs such as petroleum-gas can be ambiguous; use factorio_search_reference and choose one exact recipe ID.",
            {"item_or_recipe_id": {"type": "string"}},
            ["item_or_recipe_id"],
        ),
        _read_only_tool(
            "factorio_get_technology",
            "Return exact technology prerequisites, research cost, and unlocked recipe IDs from the run's pinned export.",
            {"technology_id": {"type": "string"}},
            ["technology_id"],
        ),
        _read_only_tool(
            "factorio_get_unlock_path",
            "Return the exact recipe ingredients, direct unlock technologies, and transitive technology prerequisite path.",
            {"item_or_recipe_id": {"type": "string"}},
            ["item_or_recipe_id"],
        ),
        _read_only_tool(
            "factorio_get_machine_requirements",
            "Return the machine category and versioned machine prototype facts required by a recipe.",
            {"recipe_id": {"type": "string"}},
            ["recipe_id"],
        ),
        _read_only_tool(
            "factorio_get_prototype",
            "Return exact prototype facts when the run export includes prototype metadata. Prototype.Lab is a valid lookup and returns the lab entity facts.",
            {"prototype_id": {"type": "string"}},
            ["prototype_id"],
        ),
        _read_only_tool(
            "factorio_memory_list",
            "List current model-managed session memory entries by optional namespace prefix.",
            {
                "prefix": {"type": "string", "default": ""},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
                "cursor": {"type": "string"},
            },
        ),
        _read_only_tool(
            "factorio_memory_read",
            "Read one model-managed session memory entry by key.",
            {"key": {"type": "string"}},
            ["key"],
        ),
        {
            "name": "factorio_memory_write",
            "description": "Create or revise one model-managed session memory entry using optimistic revision control.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "minLength": 1, "maxLength": 256},
                    "content": {"type": "string"},
                    "expected_revision": {"type": "integer", "minimum": 0},
                },
                "required": ["key", "content"],
                "additionalProperties": False,
            },
            "outputSchema": {"type": "object", "additionalProperties": True},
            "annotations": {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
        },
        {
            "name": "factorio_memory_delete",
            "description": "Delete one model-managed session memory entry using optimistic revision control.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "minLength": 1, "maxLength": 256},
                    "expected_revision": {"type": "integer", "minimum": 0},
                },
                "required": ["key"],
                "additionalProperties": False,
            },
            "outputSchema": {"type": "object", "additionalProperties": True},
            "annotations": {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False},
        },
        _read_only_tool(
            "factorio_memory_search",
            "Search model-managed session memory by key and content terms.",
            {
                "query": {"type": "string", "minLength": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "cursor": {"type": "string"},
            },
            ["query"],
        ),
        _read_only_tool(
            "factorio_memory_trace",
            "Read the append-only trace of model memory writes and deletes for this session.",
            {
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
                "cursor": {"type": "string"},
            },
        ),
    ]
)

# Keep the historical ``TOOLS`` import as the two world-action tools for
# callers that use it as a narrow execution manifest.  The MCP server and
# evaluation identity use ``ALL_TOOLS`` so every callable knowledge/memory
# surface is present in normal runs.
REFERENCE_TOOLS = TOOLS[len(_BASE_TOOLS) :]
ALL_TOOLS = list(TOOLS)
TOOLS = _BASE_TOOLS
MEMORY_TOOL_NAMES = {
    "factorio_memory_list",
    "factorio_memory_read",
    "factorio_memory_write",
    "factorio_memory_delete",
    "factorio_memory_search",
    "factorio_memory_trace",
}


def tools_for_profile(*, memory_enabled: bool | None = None) -> list[dict]:
    """Return the exact manifest exposed by the selected evaluation profile."""
    enabled = _memory_enabled() if memory_enabled is None else memory_enabled
    if enabled:
        return list(ALL_TOOLS)
    return [tool for tool in ALL_TOOLS if tool["name"] not in MEMORY_TOOL_NAMES]


def _mcp_tool_result(text: str, is_error: bool) -> dict:
    """Build a MCP result with structured content when the envd response is JSON."""

    result = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    try:
        structured = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        structured = None
    if isinstance(structured, dict):
        result["structuredContent"] = structured
    elif is_error:
        result["structuredContent"] = {"error": text}
    return result


def _reference_call(name: str, arguments: dict[str, object]) -> dict:
    api, game = _knowledge()
    if name == "factorio_search_reference":
        query = str(arguments.get("query", ""))
        kinds = arguments.get("kinds")
        if kinds is not None and not isinstance(kinds, list):
            raise ValueError("kinds must be a list")
        requested = {str(kind).lower() for kind in (kinds or [])}
        api_results = []
        if not requested or "api" in requested:
            api_results = api.search(
                query,
                kinds={"api"},
                limit=100,
            )["results"]
            for result in api_results:
                result["canonical_id"] = result.pop("document_id")
        game_results = game.search(
            query,
            kinds=requested - {"api"} if requested else None,
            limit=100,
        )["results"]
        results = sorted(api_results + game_results, key=lambda item: (item.get("kind", ""), item.get("canonical_id", "")))
        from fle.envd.knowledge import _paginate

        page, next_cursor = _paginate(results, int(arguments.get("limit", 20)), arguments.get("cursor"))
        return {
            "schema_version": "knowledge-reference-v1",
            "api_reference_id": "fle-api-reference-v1",
            "api_reference_sha256": api.reference_hash,
            "game_data_reference_id": game.reference_id,
            "game_data_reference_sha256": game.reference_hash,
            "query": query,
            "results": page,
            "next_cursor": next_cursor,
        }
    if name == "factorio_read_reference":
        document_id = str(arguments["document_id"])
        if document_id.startswith("api/") or document_id.startswith("api:") or not any(
            document_id.startswith(prefix) for prefix in ("recipe:", "technology:", "prototype:")
        ):
            return api.read(
                document_id,
                section=(str(arguments["section"]) if arguments.get("section") is not None else None),
                cursor=arguments.get("cursor"),
                max_chars=int(arguments.get("max_chars", 12000)),
            )
        kind, _, identifier = document_id.partition(":")
        if kind == "recipe":
            return game.recipe(identifier)
        if kind == "technology":
            return game.technology(identifier)
        if kind == "prototype":
            return game.prototype(identifier)
        raise KeyError(f"unknown reference document: {document_id}")
    if name == "factorio_get_recipe":
        return game.recipe(str(arguments["item_or_recipe_id"]))
    if name == "factorio_get_technology":
        return game.technology(str(arguments["technology_id"]))
    if name == "factorio_get_unlock_path":
        return game.unlock_path(str(arguments["item_or_recipe_id"]))
    if name == "factorio_get_machine_requirements":
        return game.machine_requirements(str(arguments["recipe_id"]))
    if name == "factorio_get_prototype":
        return game.prototype(str(arguments["prototype_id"]))
    raise KeyError(f"unknown reference tool: {name}")


def _memory_call(name: str, arguments: dict[str, object]) -> dict:
    if not _memory_enabled():
        raise RuntimeError(
            "session memory is disabled for this evaluation profile; "
            "rerun with --memory-profile stateful to enable it"
        )
    lease_id = os.environ.get("LEASE_ID", "")
    if name == "factorio_memory_list":
        path = _query_path(
            f"/v1/leases/{lease_id}/memory",
            {
                "prefix": arguments.get("prefix", ""),
                "limit": arguments.get("limit", 50),
                "cursor": arguments.get("cursor"),
            },
        )
        return _envd("GET", path)
    if name == "factorio_memory_read":
        return _envd(
            "GET",
            _query_path(
                f"/v1/leases/{lease_id}/memory/read", {"key": arguments["key"]}
            ),
        )
    if name == "factorio_memory_write":
        payload = {
            "key": arguments["key"],
            "content": arguments["content"],
            "expected_revision": arguments.get("expected_revision"),
        }
        return _envd("POST", f"/v1/leases/{lease_id}/memory/write", payload)
    if name == "factorio_memory_delete":
        payload = {
            "key": arguments["key"],
            "expected_revision": arguments.get("expected_revision"),
        }
        return _envd("POST", f"/v1/leases/{lease_id}/memory/delete", payload)
    if name == "factorio_memory_search":
        return _envd(
            "GET",
            _query_path(
                f"/v1/leases/{lease_id}/memory/search",
                {
                    "query": arguments["query"],
                    "limit": arguments.get("limit", 20),
                    "cursor": arguments.get("cursor"),
                },
            ),
        )
    if name == "factorio_memory_trace":
        return _envd(
            "GET",
            _query_path(
                f"/v1/leases/{lease_id}/memory/trace",
                {
                    "limit": arguments.get("limit", 100),
                    "cursor": arguments.get("cursor"),
                },
            ),
        )
    raise KeyError(f"unknown memory tool: {name}")


def _state_query_call(name: str, arguments: dict[str, object]) -> dict:
    """Forward the typed public state query to the lease-bound envd worker."""

    if name != "factorio_query_state":
        raise KeyError(f"unknown state query tool: {name}")
    lease_id = os.environ.get("LEASE_ID", "")
    values: dict[str, object] = {
        "kind": arguments["kind"],
        "item": arguments.get("item"),
        "window_seconds": arguments.get("window_seconds"),
        "since_revision": arguments.get("since_revision"),
        "entity_type": arguments.get("entity_type"),
        "area": (
            json.dumps(arguments["area"], separators=(",", ":"))
            if arguments.get("area") is not None
            else None
        ),
        "changed_since": arguments.get("changed_since"),
        "limit": arguments.get("limit", 32),
    }
    return _envd(
        "GET",
        _query_path(f"/v1/leases/{lease_id}/state/query", values),
    )


def _negotiate_protocol_version(requested: object) -> str:
    """Select a client-supported MCP revision without rejecting older clients."""

    if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return PROTOCOL_VERSION


def _call_tool(
    name: str,
    arguments: dict,
    *,
    request_id: object | None = None,
) -> tuple[str, bool]:
    lease_id = os.environ.get("LEASE_ID", "")
    _trace(f"tools/call name={name!r} args={json.dumps(arguments, default=str)[:200]}")
    try:
        reference_name = next(
            (
                candidate
                for candidate in (
                    "factorio_search_reference",
                    "factorio_read_reference",
                    "factorio_get_recipe",
                    "factorio_get_technology",
                    "factorio_get_unlock_path",
                    "factorio_get_machine_requirements",
                    "factorio_get_prototype",
                )
                if name.endswith(candidate)
            ),
            None,
        )
        if reference_name is not None:
            return _bounded_json_text(_reference_call(reference_name, arguments)), False
        memory_name = next(
            (
                candidate
                for candidate in (
                    "factorio_memory_list",
                    "factorio_memory_read",
                    "factorio_memory_write",
                    "factorio_memory_delete",
                    "factorio_memory_search",
                    "factorio_memory_trace",
                )
                if name.endswith(candidate)
            ),
            None,
        )
        if memory_name is not None:
            return _bounded_json_text(_memory_call(memory_name, arguments)), False
        if name.endswith("factorio_query_state"):
            return _bounded_json_text(
                _state_query_call("factorio_query_state", arguments)
            ), False
        if name.endswith("factorio_observe_factory"):
            observation = _envd(
                "GET",
                _query_path(
                    f"/v1/leases/{lease_id}/observe",
                    {
                        "cursor": arguments.get("cursor"),
                        "keyframe": "true" if arguments.get("keyframe") else None,
                    },
                ),
            )
            adaptive_order = next(
                (
                    contract
                    for contract in observation.get("contracts", [])
                    if contract.get("order_id") == "epoch-order"
                ),
                None,
            )
            if adaptive_order and adaptive_order.get("status") != "open":
                _signal_epoch_terminal(
                    f"contract_{adaptive_order.get('status')}", observation
                )
            return _bounded_json_text(observation), False
        if name.endswith("factorio_check_throughput"):
            payload = {}
            if request_id is not None:
                payload["request_id"] = f"mcp-throughput:{request_id}"
            result = _envd(
                "POST",
                f"/v1/leases/{lease_id}/throughput-check",
                payload,
            )
            if result.get("contract_status") != "open":
                _signal_epoch_terminal(
                    f"contract_{result.get('contract_status')}", result
                )
            return _bounded_json_text(result), False
        if name.endswith("factorio_execute_program"):
            code = arguments.get("code")
            if not isinstance(code, str) or not code.strip():
                # Weak models sometimes send 'program' or 'script'; accept
                # obvious aliases rather than burning their retry budget.
                for alias in ("program", "script", "python"):
                    candidate = arguments.get(alias)
                    if isinstance(candidate, str) and candidate.strip():
                        code = candidate
                        break
            if not isinstance(code, str) or not code.strip():
                return "error: execute requires non-empty 'code'", True
            fingerprint = _program_fingerprint(code)
            if (
                fingerprint == _last_failure_fingerprint
                and _consecutive_failure_count >= REPEATED_FAILURE_LIMIT
            ):
                _trace(
                    "repetition circuit breaker blocked program "
                    f"fingerprint={fingerprint[:12]} count={_consecutive_failure_count}"
                )
                return _repetition_error(_consecutive_failure_count), True
            # Body schema is {code} only: lease identity comes from the URL
            # path, and the wire model forbids extra fields (422 otherwise).
            execute_payload = {"code": code}
            if request_id is not None:
                execute_payload["request_id"] = _next_execute_request_id(request_id)
            result = _envd(
                "POST",
                f"/v1/leases/{lease_id}/execute",
                execute_payload,
            )
            event_failed = bool((result.get("event") or {}).get("error"))
            failure_count = _record_execution_result(fingerprint, event_failed)
            if result.get("terminal_reason"):
                _signal_epoch_terminal(str(result["terminal_reason"]), result)
            else:
                adaptive_terminal = next(
                    (
                        event.get("kind")
                        for event in result.get("events", [])
                        if event.get("kind")
                        in {"contract_fulfilled", "contract_expired"}
                    ),
                    None,
                )
                if adaptive_terminal:
                    _signal_epoch_terminal(str(adaptive_terminal), result)
            text = _bounded_json_text(result)
            if event_failed and failure_count >= REPEATED_FAILURE_LIMIT:
                text += "\n\n" + _repetition_error(failure_count)
            return text, event_failed
        return f"error: unknown tool {name}", True
    except Exception as exc:  # noqa: BLE001 - surfaced to the model as text
        return f"tool error: {type(exc).__name__}: {exc}", True


def main() -> None:
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = message.get("method")
        msg_id = message.get("id")
        if method == "initialize":
            result = {
                "protocolVersion": _negotiate_protocol_version(
                    (message.get("params") or {}).get("protocolVersion")
                ),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "factorio-envd-mcp", "version": "0.1.0"},
                "instructions": (
                    "This lease-bound server exposes direct observe/execute, "
                    "bounded public state retrieval, "
                    "callable API/game-data reference, and optional session "
                    "memory tools. Its stdio dispatcher is a FIFO queue; envd accepts "
                    "concurrent HTTP requests but serializes all operations for "
                    "one lease. Use the execute tool's code argument for "
                    "synchronous programmatic FLE action composition. Memory is "
                    "disabled unless MEMORY_ENABLED is set by the evaluation profile."
                ),
            }
        elif method == "tools/list":
            result = {"tools": tools_for_profile()}
        elif method == "tools/call":
            params = message.get("params") or {}
            text, is_error = _call_tool(
                str(params.get("name")),
                params.get("arguments") or {},
                request_id=msg_id,
            )
            result = _mcp_tool_result(text, is_error)
        elif method == "ping":
            result = {}
        elif msg_id is None:
            continue  # notification
        else:
            result = None
        if msg_id is None:
            continue
        response = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result if result is not None else {},
        }
        if method and method not in {
            "initialize",
            "tools/list",
            "tools/call",
            "ping",
        }:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"unknown method {method}"},
            }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
