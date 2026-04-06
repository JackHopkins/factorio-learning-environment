#!/usr/bin/env python3
"""FLE Bridge Service - Persistent HTTP daemon inside the Inspect sandbox container.

Maintains FactorioInstance and FactorioGymEnv state. Serves requests over a Unix
domain socket at /tmp/fle_bridge.sock. The bridge_client.py CLI communicates with
this daemon, and is invoked by the host-side solver via sandbox().exec().
"""

import json
import logging
import os
import socket
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
import gym


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that converts numpy types to native Python types."""

    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return str(obj)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("fle_bridge")

# --- Unix domain socket HTTP server ---

class UnixHTTPServer(HTTPServer):
    address_family = socket.AF_UNIX

    def server_bind(self):
        if os.path.exists(self.server_address):
            os.unlink(self.server_address)
        super().server_bind()
        os.chmod(self.server_address, 0o666)

    def get_request(self):
        request, client_address = super().get_request()
        return request, ("127.0.0.1", 0)


# --- Globals set during init ---

_gym_env = None
_instance = None
_game_states = []  # Rolling list for error recovery


def _wait_for_rcon(host="localhost", port=27015, timeout=180):
    """Block until Factorio RCON is reachable."""
    logger.info("Waiting for Factorio RCON on %s:%d ...", host, port)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            logger.info("RCON is reachable.")
            return True
        except OSError:
            time.sleep(2)
    raise RuntimeError(f"Factorio RCON not available after {timeout}s")


def _init_environment():
    """Create FactorioInstance + FactorioGymEnv from environment variables."""
    global _gym_env, _instance

    env_id = os.environ.get("FLE_ENV_ID", "iron_ore_throughput")
    scenario = os.environ.get("FLE_SCENARIO", "default_lab_scenario")
    num_agents = int(os.environ.get("FLE_NUM_AGENTS", "1"))

    # For unbounded/open-play tasks, the gym environment is always "open_play"
    # which uses DefaultTask. The env_id (e.g. "open_play_production") is just
    # for task identification in the Inspect eval set.
    from fle.eval.tasks.task_definitions.unbounded.unbounded_tasks import UNBOUNDED_PRODUCTION_TASKS
    if env_id in UNBOUNDED_PRODUCTION_TASKS:
        task_key = "open_play"
    else:
        task_key = env_id

    logger.info("Initialising environment: env_id=%s, task_key=%s, scenario=%s, num_agents=%d",
                env_id, task_key, scenario, num_agents)

    _wait_for_rcon()

    from fle.env import FactorioInstance
    from fle.env.gym_env.environment import FactorioGymEnv
    from fle.eval.tasks import TaskFactory

    _instance = FactorioInstance(
        address="localhost",
        tcp_port=27015,
        fast=True,
        cache_scripts=True,
        inventory={},
        all_technologies_researched=False,
        num_agents=num_agents,
    )
    _instance.set_speed_and_unpause(10)

    task = TaskFactory.create_task(task_key)
    task.setup(_instance)

    _gym_env = FactorioGymEnv(instance=_instance, task=task, enable_vision=True)
    _gym_env.reset()

    logger.info("Environment ready (env_id=%s)", env_id)


# --- Request handler ---

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the bridge service."""

    # Suppress per-request logs to stderr
    def log_message(self, fmt, *args):
        logger.debug(fmt, *args)

    def _send_json(self, data, status=200):
        body = json.dumps(data, cls=_NumpyEncoder).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    # ----- GET routes -----

    def do_GET(self):
        try:
            if self.path == "/health":
                self._handle_health()
            elif self.path == "/observe":
                self._handle_observe()
            elif self.path == "/score":
                self._handle_score()
            elif self.path == "/system-prompt":
                self._handle_system_prompt()
            elif self.path == "/game-state":
                self._handle_game_state()
            else:
                self._send_json({"error": f"Unknown GET path: {self.path}"}, 404)
        except Exception as exc:
            logger.error("GET %s error: %s", self.path, exc, exc_info=True)
            self._send_json({"error": str(exc), "traceback": traceback.format_exc()}, 500)

    # ----- POST routes -----

    def do_POST(self):
        try:
            if self.path == "/execute":
                self._handle_execute()
            elif self.path == "/reset":
                self._handle_reset()
            elif self.path == "/screenshot":
                self._handle_screenshot()
            else:
                self._send_json({"error": f"Unknown POST path: {self.path}"}, 404)
        except Exception as exc:
            logger.error("POST %s error: %s", self.path, exc, exc_info=True)
            self._send_json({"error": str(exc), "traceback": traceback.format_exc()}, 500)

    # ----- Handler implementations -----

    def _handle_health(self):
        ready = _gym_env is not None
        self._send_json({"status": "ok" if ready else "initialising"})

    def _handle_observe(self):
        try:
            obs = _gym_env.get_observation()
        except Exception as e:
            # If vision rendering fails (e.g. no sprites), retry with vision disabled
            if _gym_env.enable_vision:
                logger.warning("get_observation() failed with vision enabled (%s), retrying without vision", e)
                _gym_env.enable_vision = False
                obs = _gym_env.get_observation()
            else:
                raise
        obs_dict = obs.to_dict()
        # Strip bulky map_image from observation to reduce payload;
        # the solver doesn't use it through the bridge (uses /screenshot instead).
        obs_dict.pop("map_image", None)
        # Fix Observation.to_dict() quirks that break from_dict() round-trip:
        # - "progress" and "current_research" can be the string "None" instead of
        #   a proper null/empty value, causing from_dict() to iterate over characters.
        research = obs_dict.get("research", {})
        if isinstance(research, dict):
            if research.get("progress") == "None" or not isinstance(research.get("progress"), list):
                research["progress"] = []
            if research.get("current_research") == "None":
                research["current_research"] = None
        self._send_json(obs_dict)

    def _handle_score(self):
        score, automated = _instance.namespaces[0].score()
        self._send_json({
            "production_score": score,
            "automated_production_score": automated or 0,
        })

    def _handle_system_prompt(self):
        import importlib.resources
        from fle.env.utils.controller_loader.system_prompt_generator import SystemPromptGenerator

        generator = SystemPromptGenerator(
            str(importlib.resources.files("fle") / "env")
        )
        prompt = generator.generate_for_agent(agent_idx=0, num_agents=1)
        self._send_json({"system_prompt": prompt})

    def _handle_game_state(self):
        from fle.commons.models.game_state import GameState
        gs = GameState.from_instance(_instance)
        self._send_json({"game_state": gs.to_raw()})

    def _handle_execute(self):
        body = self._read_body()
        code = body.get("code", "")
        agent_idx = body.get("agent_idx", 0)

        from fle.env.gym_env.action import Action
        from fle.commons.models.game_state import GameState
        from fle.env.gym_env.observation_formatter import TreeObservationFormatter

        action = Action(agent_idx=agent_idx, code=code)

        obs, reward, terminated, truncated, info = _gym_env.step(action)
        _gym_env.background_step()

        # Capture game state for rollback
        output_game_state = info.get("output_game_state")
        game_state_raw = output_game_state.to_raw() if output_game_state else None
        _game_states.append(output_game_state)
        # Keep last 5 states
        if len(_game_states) > 5:
            _game_states.pop(0)

        # Format flows
        flow = obs.get("flows", {})
        flows_formatted = TreeObservationFormatter.format_flows_compact(flow)

        result = {
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "result": info.get("result", ""),
            "production_score": info.get("production_score", 0),
            "automated_production_score": info.get("automated_production_score", 0),
            "policy_execution_time": info.get("policy_execution_time", 0),
            "error_occurred": info.get("error_occurred", False),
            "flows": flow,
            "flows_formatted": flows_formatted,
            "score": obs.get("score", 0),
            "ticks": info.get("ticks", 0),
            "game_state_raw": game_state_raw,
        }

        self._send_json(result)

    def _handle_reset(self):
        body = self._read_body()
        game_state_raw = body.get("game_state", None)

        if game_state_raw:
            from fle.commons.models.game_state import GameState
            gs = GameState.parse_raw(game_state_raw)
            _gym_env.reset({"game_state": gs})
        else:
            _gym_env.reset()

        _game_states.clear()
        self._send_json({"status": "ok"})

    def _handle_screenshot(self):
        namespace = _instance.namespaces[0]
        result = namespace._render(radius=64, max_render_radius=32, include_status=True)
        base64_data = result.to_base64()
        # Write to file for sandbox().read_file()
        with open("/tmp/screenshot.png", "wb") as f:
            import base64
            f.write(base64.b64decode(base64_data))
        self._send_json({
            "path": "/tmp/screenshot.png",
            "base64": f"data:image/png;base64,{base64_data}",
        })


# --- Main ---

def main():
    sock_path = "/tmp/fle_bridge.sock"

    logger.info("Starting FLE Bridge Service on %s", sock_path)

    # Initialise the environment (blocks until RCON is available)
    try:
        _init_environment()
    except Exception:
        logger.error("Failed to initialise environment:\n%s", traceback.format_exc())
        sys.exit(1)

    server = UnixHTTPServer(sock_path, BridgeHandler)
    logger.info("Bridge service listening on %s", sock_path)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down bridge service.")
    finally:
        server.server_close()
        if os.path.exists(sock_path):
            os.unlink(sock_path)


if __name__ == "__main__":
    main()
