#!/usr/bin/env python3
"""FLE Bridge Client - Thin CLI for communicating with bridge_service.py.

Invoked inside the container via sandbox().exec():
    python3 /opt/fle/bridge_client.py health
    python3 /opt/fle/bridge_client.py execute '{"code": "...", "agent_idx": 0}'
    python3 /opt/fle/bridge_client.py observe
    python3 /opt/fle/bridge_client.py reset '{"task_key": "iron_ore_throughput"}'
    python3 /opt/fle/bridge_client.py score
    python3 /opt/fle/bridge_client.py screenshot
    python3 /opt/fle/bridge_client.py system-prompt
    python3 /opt/fle/bridge_client.py game-state

Prints JSON response to stdout for capture by sandbox().exec().
"""

import http.client
import json
import socket
import sys


SOCK_PATH = "/tmp/fle_bridge.sock"


class UnixHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over a Unix domain socket."""

    def __init__(self, sock_path, timeout=300):
        super().__init__("localhost", timeout=timeout)
        self._sock_path = sock_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._sock_path)


def request(method, path, body=None, timeout=300):
    try:
        conn = UnixHTTPConnection(SOCK_PATH, timeout=timeout)
        headers = {}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(payload))
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode()
        conn.close()
    except (ConnectionRefusedError, FileNotFoundError, OSError) as e:
        # Bridge socket not available yet (service still starting)
        print(json.dumps({"error": f"Bridge not available: {e}", "status": "unavailable"}), flush=True)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Connection error: {e}", "status": "error"}), flush=True)
        sys.exit(1)

    if resp.status >= 400:
        print(json.dumps({"error": data, "status": resp.status}), flush=True)
        sys.exit(1)
    return data


# Map command names to (method, path)
COMMANDS = {
    "health":        ("GET",  "/health"),
    "observe":       ("GET",  "/observe"),
    "score":         ("GET",  "/score"),
    "system-prompt": ("GET",  "/system-prompt"),
    "game-state":    ("GET",  "/game-state"),
    "execute":       ("POST", "/execute"),
    "reset":         ("POST", "/reset"),
    "screenshot":    ("POST", "/screenshot"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        cmds = ", ".join(sorted(COMMANDS))
        print(json.dumps({"error": f"Usage: bridge_client.py <{cmds}> [json_body]"}),
              flush=True)
        sys.exit(1)

    cmd = sys.argv[1]
    method, path = COMMANDS[cmd]

    body = None
    if len(sys.argv) >= 3:
        try:
            body = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid JSON argument: {e}"}), flush=True)
            sys.exit(1)

    data = request(method, path, body=body)
    # Print raw JSON to stdout
    print(data, flush=True)


if __name__ == "__main__":
    main()