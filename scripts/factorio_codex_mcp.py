"""Minimal stdio MCP server exposing two Factorio envd tools to Codex.

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
import urllib.request

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

_last_failure_fingerprint: str | None = None
_consecutive_failure_count = 0
_process_nonce = hashlib.sha256(
    f"{os.getpid()}:{time.time_ns()}".encode("utf-8")
).hexdigest()[:16]
_tool_call_sequence = 0


def _reset_repetition_state() -> None:
    global _last_failure_fingerprint, _consecutive_failure_count
    _last_failure_fingerprint = None
    _consecutive_failure_count = 0


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
        except (urllib.error.URLError, TimeoutError) as exc:
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


def _bounded_json_text(payload: dict, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    """Serialize a payload without ever cutting JSON in the middle of a token."""

    serialized = json.dumps(payload, default=str, separators=(",", ":"))
    if len(serialized) <= max_chars:
        return serialized

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def envelope(prefix_chars: int) -> str:
        return json.dumps(
            {
                "truncated": True,
                "original_json_chars": len(serialized),
                "original_json_sha256": digest,
                "json_prefix": serialized[:prefix_chars],
            },
            separators=(",", ":"),
        )

    low, high = 0, min(len(serialized), max_chars)
    best = envelope(0)
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
            "production statistics, open customer contracts, blueprint library, "
            "ticks, and state hash. Safe to request concurrently with other "
            "calls; envd still serializes operations for one lease."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
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
]


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
        if name.endswith("factorio_observe_factory"):
            observation = _envd("GET", f"/v1/leases/{lease_id}/observe")
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
                    "This lease-bound server exposes direct observe and execute "
                    "tools. Its stdio dispatcher is a FIFO queue; envd accepts "
                    "concurrent HTTP requests but serializes all operations for "
                    "one lease. Use the execute tool's code argument for "
                    "synchronous programmatic FLE action composition."
                ),
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
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
