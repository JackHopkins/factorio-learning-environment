"""Minimal stdio MCP server exposing two Factorio envd tools to Codex.

Newline-delimited JSON-RPC 2.0 (current MCP stdio transport), no third-party
dependencies. The lease is created by the outer harness runner; this process
only observes/executes against ENVD_URL for LEASE_ID.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

PROTOCOL_VERSION = "2024-11-05"


def _envd(method: str, path: str, payload: dict | None = None) -> dict:
    url = os.environ["ENVD_URL"].rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))
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


TOOLS = [
    {
        "name": "factorio_observe_factory",
        "description": (
            "Observe the current Factorio factory state: inventory, production "
            "statistics, open customer contracts, blueprint library, ticks."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "factorio_execute_program",
        "description": (
            "Execute one short Python program inside the sandboxed Factorio "
            "REPL. Available names include inspect_inventory, get_entities, "
            "nearest, move_to, harvest_resource, craft_item, place_entity, "
            "place_entity_next_to, insert_item, extract_item, set_entity_recipe, "
            "connect_entities, get_resource_patch, set_research, sleep, print. "
            "One intervention per call; the program's printed output returns."
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
    },
]


def _call_tool(name: str, arguments: dict) -> tuple[str, bool]:
    lease_id = os.environ.get("LEASE_ID", "")
    _trace(f"tools/call name={name!r} args={json.dumps(arguments, default=str)[:200]}")
    try:
        if name.endswith("factorio_observe_factory"):
            observation = _envd("GET", f"/v1/leases/{lease_id}/observe")
            return json.dumps(observation, default=str)[:60_000], False
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
            # Body schema is {code} only: lease identity comes from the URL
            # path, and the wire model forbids extra fields (422 otherwise).
            result = _envd(
                "POST",
                f"/v1/leases/{lease_id}/execute",
                {"code": code},
            )
            return json.dumps(result, default=str)[:60_000], False
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
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "factorio-envd-mcp", "version": "0.1.0"},
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            text, is_error = _call_tool(
                str(params.get("name")), params.get("arguments") or {}
            )
            result = {
                "content": [{"type": "text", "text": text}],
                "isError": is_error,
            }
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
