#!/usr/bin/env python
"""
FLE Trajectory Viewer — browse agent runs, screenshots, and videos.

Usage:
    python viewer.py          # serves on http://localhost:5050
    python viewer.py --port 8080
"""

import json
import re
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, send_file, abort

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
FLE_DIR = BASE_DIR / ".fle"
DB_PATH = FLE_DIR / "data.db"
TRAJ_DIR = FLE_DIR / "trajectory_logs"
SCREEN_DIR = FLE_DIR / "run_screenshots"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _remove_whitespace_blocks(messages):
    """Mirror APIFactory preprocessing for exact prompt payload reconstruction."""
    out = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            if content.strip():
                out.append(message)
        elif isinstance(content, list):
            if len(content) > 0:
                out.append(message)
        else:
            out.append(message)
    return out


def _merge_contiguous_messages(messages):
    """Mirror APIFactory preprocessing for exact prompt payload reconstruction."""
    if not messages:
        return messages

    merged = [dict(messages[0])]
    for message in messages[1:]:
        prev = merged[-1]
        if (
            message.get("role") == prev.get("role")
            and isinstance(prev.get("content"), str)
            and isinstance(message.get("content"), str)
        ):
            prev["content"] += "\n\n" + message["content"]
        else:
            merged.append(dict(message))
    return merged


def _normalized_llm_messages(raw_messages):
    return _merge_contiguous_messages(_remove_whitespace_blocks(raw_messages))


def _step_numbers_for_version(version: int, row_count: int):
    """Best-effort canonical step numbers from trajectory logs; fallback to row order."""
    traj_path = TRAJ_DIR / f"v{version}"
    iter_steps = sorted(
        int(m.group(1))
        for p in traj_path.glob("agent0_iter*_program.py")
        for m in [re.match(r"agent0_iter(\d+)_program\.py$", p.name)]
        if m
    )
    if not iter_steps:
        return list(range(row_count))

    step_numbers = []
    for idx in range(row_count):
        if idx < len(iter_steps):
            step_numbers.append(iter_steps[idx])
        else:
            step_numbers.append(iter_steps[-1] + (idx - len(iter_steps) + 1))
    return step_numbers


# ── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/runs")
def api_runs():
    conn = get_db()
    rows = conn.execute("""
        SELECT version, model, version_description,
               MAX(depth) as max_depth,
               MAX(value) as max_reward,
               MIN(created_at) as created_at
        FROM programs GROUP BY version ORDER BY version DESC
    """).fetchall()

    runs = []
    for r in rows:
        v = r["version"]
        desc = r["version_description"] or ""
        task = ""
        for line in desc.split("\n"):
            if line.startswith("type:"):
                task = line[5:]

        # Count trajectory log files
        traj_path = TRAJ_DIR / f"v{v}"
        steps = len(list(traj_path.glob("agent0_iter*_program.py"))) if traj_path.is_dir() else 0

        # Check screenshots/video
        screen_path = SCREEN_DIR / f"v{v}"
        has_screenshots = screen_path.is_dir() and any(screen_path.glob("step_*.png"))
        has_video = (screen_path / "run.mp4").is_file() if screen_path.is_dir() else False

        # Get max production_score from meta
        meta_rows = conn.execute(
            "SELECT meta FROM programs WHERE version=? ORDER BY depth", (v,)
        ).fetchall()
        scores = []
        max_score = 0
        for mr in meta_rows:
            if mr["meta"]:
                m = json.loads(mr["meta"])
                s = m.get("production_score", 0)
                scores.append(s)
                max_score = max(max_score, s)

        runs.append({
            "version": v,
            "model": r["model"],
            "task": task,
            "steps": steps,
            "max_reward": round(r["max_reward"], 2),
            "max_score": max_score,
            "has_video": has_video,
            "has_screenshots": has_screenshots,
            "created_at": r["created_at"],
        })

    conn.close()
    return jsonify(runs)


@app.route("/api/run/<int:version>/steps")
def api_run_steps(version):
    conn = get_db()
    rows = conn.execute(
        "SELECT depth, value, code, meta, response, conversation_json, created_at "
        "FROM programs WHERE version=? ORDER BY created_at, rowid",
        (version,),
    ).fetchall()

    traj_path = TRAJ_DIR / f"v{version}"
    step_numbers = _step_numbers_for_version(version, len(rows))

    # Read system prompt if available
    sys_prompt_file = traj_path / "agent0_system_prompt.txt"
    system_prompt = sys_prompt_file.read_text() if sys_prompt_file.is_file() else ""

    steps = []
    for turn_idx, r in enumerate(rows):
        step = step_numbers[turn_idx]
        try:
            meta = json.loads(r["meta"]) if r["meta"] else {}
        except json.JSONDecodeError:
            meta = {}

        # Read observation from trajectory log
        obs_file = traj_path / f"agent0_iter{step}_observation.txt"
        observation = obs_file.read_text() if obs_file.is_file() else ""

        # Check screenshot
        screen_path = SCREEN_DIR / f"v{version}" / f"step_{step:03d}.png"

        conv_msgs = []
        if r["conversation_json"]:
            try:
                conv_msgs = json.loads(r["conversation_json"]).get("messages", [])
            except (json.JSONDecodeError, KeyError, IndexError):
                conv_msgs = []

        steps.append({
            "step": step,
            "reward": round(r["value"], 2),
            "production_score": meta.get("production_score", 0),
            "error": meta.get("error_occurred", False),
            "code": r["code"] or "",
            "observation": observation,
            "agent_response": "",
            "exec_output": r["response"] or "",
            "has_screenshot": screen_path.is_file(),
            "created_at": r["created_at"],
            "_conversation_messages": conv_msgs,
        })

    # Second pass: extract agent response from the NEXT row conversation tail.
    # At step N+1 input, tail is [..., assistant(step N), user(step N+1)].
    for i, s in enumerate(steps):
        next_msgs = (
            steps[i + 1]["_conversation_messages"] if i + 1 < len(steps) else []
        )

        if (
            len(next_msgs) >= 2
            and isinstance(next_msgs[-1], dict)
            and isinstance(next_msgs[-2], dict)
            and next_msgs[-1].get("role") == "user"
            and next_msgs[-2].get("role") == "assistant"
        ):
            s["agent_response"] = next_msgs[-2].get("content", "")
        elif next_msgs:
            for msg in reversed(next_msgs):
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    s["agent_response"] = msg.get("content", "")
                    break

        del s["_conversation_messages"]

    conn.close()
    return jsonify({"system_prompt": system_prompt, "steps": steps})


@app.route("/api/run/<int:version>/prompt/<int:step>")
def api_run_prompt(version, step):
    """Return the exact normalized messages payload sent to the LLM for a step."""
    conn = get_db()
    rows = conn.execute(
        "SELECT conversation_json, model, created_at "
        "FROM programs WHERE version=? ORDER BY created_at, rowid",
        (version,),
    ).fetchall()
    conn.close()

    if not rows:
        abort(404)

    step_numbers = _step_numbers_for_version(version, len(rows))
    try:
        row_idx = step_numbers.index(step)
    except ValueError:
        abort(404)

    row = rows[row_idx]
    raw_messages = []
    if row["conversation_json"]:
        try:
            raw_messages = json.loads(row["conversation_json"]).get("messages", [])
        except (json.JSONDecodeError, KeyError, TypeError):
            raw_messages = []

    messages = _normalized_llm_messages(raw_messages)
    return jsonify(
        {
            "version": version,
            "step": step,
            "created_at": row["created_at"],
            "model": row["model"],
            "message_count": len(messages),
            "messages": messages,
        }
    )


@app.route("/api/run/<int:version>/mode-events")
def api_run_mode_events(version):
    traj_path = TRAJ_DIR / f"v{version}"
    mode_path = traj_path / "mode_events.jsonl"

    events = []
    if mode_path.is_file():
        for line in mode_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append(
                    {
                        "event_type": "PARSE_ERROR",
                        "raw_line": line,
                    }
                )

    return jsonify({"version": version, "events": events})


@app.route("/api/run/<int:version>/screenshot/<int:step>")
def api_screenshot(version, step):
    path = SCREEN_DIR / f"v{version}" / f"step_{step:03d}.png"
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="image/png")


@app.route("/api/run/<int:version>/video")
def api_video(version):
    path = SCREEN_DIR / f"v{version}" / "run.mp4"
    if not path.is_file():
        abort(404)
    return send_file(path, mimetype="video/mp4")


# ── HTML ─────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FLE Trajectory Viewer</title>
<style>
:root {
  --bg: #1a1a1a; --bg2: #232323; --bg3: #2d2d2d; --bg4: #383838;
  --fg: #d4d4d4; --fg2: #999; --accent: #f5a623; --accent2: #e8912a;
  --green: #4ec970; --red: #e55; --blue: #5ca5e8;
  --border: #3a3a3a; --code-bg: #1e1e1e;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'SF Mono', 'Consolas', 'Monaco', monospace; background: var(--bg); color: var(--fg); height: 100vh; overflow: hidden; }
a { color: var(--accent); text-decoration: none; }

/* Layout */
.app { display: flex; height: 100vh; }
.sidebar { width: 300px; min-width: 300px; background: var(--bg2); border-right: 1px solid var(--border); display: flex; flex-direction: column; }
.main { flex: 1; overflow-y: auto; padding: 20px; }

/* Sidebar */
.sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); }
.sidebar-header h1 { font-size: 16px; color: var(--accent); letter-spacing: 1px; }
.sidebar-header .sub { font-size: 11px; color: var(--fg2); margin-top: 4px; }
.run-list { flex: 1; overflow-y: auto; }
.run-item { padding: 12px 16px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.15s; }
.run-item:hover { background: var(--bg3); }
.run-item.active { background: var(--bg4); border-left: 3px solid var(--accent); }
.run-item .top { display: flex; justify-content: space-between; align-items: center; }
.run-item .version { font-weight: bold; font-size: 14px; }
.run-item .model { font-size: 11px; color: var(--fg2); margin-top: 2px; }
.run-item .task { font-size: 11px; color: var(--blue); margin-top: 2px; }
.run-item .stats { display: flex; gap: 8px; margin-top: 6px; font-size: 11px; }
.badge { padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
.badge-score { background: var(--accent); color: #000; }
.badge-steps { background: var(--bg4); color: var(--fg2); }
.badge-video { background: var(--green); color: #000; }

/* Main area */
.placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--fg2); font-size: 14px; }

/* Video */
.video-section { margin-bottom: 20px; }
.video-section video { width: 100%; max-height: 400px; border-radius: 6px; background: #000; }

/* Screenshot navigation */
.screenshot-section { margin-bottom: 20px; }
.screenshot-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.screenshot-nav button { background: var(--bg3); border: 1px solid var(--border); color: var(--fg); padding: 6px 14px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 13px; }
.screenshot-nav button:hover { background: var(--bg4); }
.screenshot-nav button:disabled { opacity: 0.3; cursor: default; }
.screenshot-nav .step-label { font-size: 13px; color: var(--fg2); }
.screenshot-img { width: 100%; border-radius: 6px; background: #000; min-height: 100px; }

/* Filmstrip */
.filmstrip { display: flex; gap: 4px; overflow-x: auto; padding: 8px 0; margin-bottom: 10px; }
.filmstrip-thumb { width: 80px; height: 45px; border-radius: 3px; cursor: pointer; border: 2px solid transparent; object-fit: cover; opacity: 0.6; transition: all 0.15s; flex-shrink: 0; }
.filmstrip-thumb:hover { opacity: 0.9; }
.filmstrip-thumb.active { border-color: var(--accent); opacity: 1; }

/* Reward timeline */
.timeline { margin-bottom: 20px; }
.timeline-label { font-size: 11px; color: var(--fg2); margin-bottom: 6px; }
.timeline-bar { display: flex; height: 28px; border-radius: 4px; overflow: hidden; background: var(--bg3); }
.timeline-seg { display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; cursor: pointer; transition: filter 0.15s; min-width: 2px; }
.timeline-seg:hover { filter: brightness(1.2); }
.timeline-seg.active { outline: 2px solid #fff; outline-offset: -2px; }

/* Code/Obs panels */
.panels { display: flex; gap: 16px; }
.panel { flex: 1; min-width: 0; }
.panel-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: var(--bg3); border-radius: 6px 6px 0 0; border: 1px solid var(--border); border-bottom: none; }
.panel-header h3 { font-size: 12px; color: var(--fg2); text-transform: uppercase; letter-spacing: 1px; }
.panel-header .meta { font-size: 11px; }
.panel-content { background: var(--code-bg); border: 1px solid var(--border); border-radius: 0 0 6px 6px; padding: 12px; overflow: auto; max-height: 500px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
.error-indicator { color: var(--red); }
.ok-indicator { color: var(--green); }

/* Section header */
.section-header { font-size: 13px; color: var(--fg2); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px; }

/* Step selector (for runs without screenshots) */
.step-selector { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 16px; }
.step-btn { background: var(--bg3); border: 1px solid var(--border); color: var(--fg); padding: 4px 10px; border-radius: 3px; cursor: pointer; font-family: inherit; font-size: 12px; }
.step-btn:hover { background: var(--bg4); }
.step-btn.active { background: var(--accent); color: #000; border-color: var(--accent); }
.step-btn.error { border-color: var(--red); }

/* View toggle */
.view-toggle { display: flex; gap: 2px; margin-bottom: 16px; background: var(--bg3); border-radius: 6px; padding: 3px; width: fit-content; }
.view-toggle button { background: transparent; border: none; color: var(--fg2); padding: 6px 16px; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: 12px; font-weight: bold; letter-spacing: 0.5px; transition: all 0.15s; }
.view-toggle button:hover { color: var(--fg); }
.view-toggle button.active { background: var(--accent); color: #000; }

/* Chain view */
.chain { padding-bottom: 40px; }
.chain-system { margin-bottom: 24px; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
.chain-system-header { padding: 8px 12px; background: var(--bg4); font-size: 11px; color: var(--fg2); text-transform: uppercase; letter-spacing: 1px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
.chain-system-header:hover { background: #444; }
.chain-system-body { background: var(--code-bg); padding: 12px; font-size: 11px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 300px; overflow-y: auto; display: none; }
.chain-system-body.open { display: block; }
.chain-step { margin-bottom: 16px; border-left: 3px solid var(--border); padding-left: 16px; position: relative; }
.chain-step.has-error { border-left-color: var(--red); }
.chain-step-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; padding: 6px 0; position: sticky; top: 0; background: var(--bg); z-index: 1; }
.chain-step-num { font-size: 12px; font-weight: bold; color: var(--accent); min-width: 55px; }
.chain-step-score { font-size: 11px; padding: 2px 8px; border-radius: 3px; font-weight: bold; }
.chain-step-error { font-size: 10px; color: var(--red); font-weight: bold; }
.chain-step-time { font-size: 10px; color: var(--fg2); margin-left: auto; }
.chain-screenshot { margin-bottom: 10px; }
.chain-screenshot img { max-width: 100%; max-height: 300px; border-radius: 4px; cursor: pointer; transition: max-height 0.3s; }
.chain-screenshot img.expanded { max-height: none; }
.chain-block { margin-bottom: 10px; }
.chain-block-label { font-size: 10px; color: var(--fg2); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; padding: 4px 8px; background: var(--bg3); border-radius: 4px 4px 0 0; display: inline-block; }
.chain-block-content { background: var(--code-bg); border: 1px solid var(--border); border-radius: 0 4px 4px 4px; padding: 10px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }
.chain-block-content.code-block { color: #ce9178; }
.chain-block-content.obs-block { color: var(--fg); }
.chain-block-content.prompt-block { color: #9cdcfe; }
.prompt-split { display: grid; gap: 10px; }
.prompt-split-box { border: 1px solid var(--border); border-radius: 6px; overflow: hidden; background: var(--code-bg); }
.prompt-split-title { font-size: 10px; color: var(--fg2); text-transform: uppercase; letter-spacing: 1px; padding: 6px 10px; background: var(--bg3); border-bottom: 1px solid var(--border); }
.prompt-split-body { padding: 10px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 320px; overflow-y: auto; }
.prompt-split-body.system { color: #b5cea8; }
.prompt-split-body.user { color: #9cdcfe; }
.prompt-mode-row { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-bottom: 1px solid var(--border); background: var(--bg2); flex-wrap: wrap; }
.prompt-mode-badge { font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: bold; border-radius: 999px; padding: 3px 8px; }
.prompt-mode-badge.mode-orchestrator { background: rgba(92,165,232,0.20); color: #b9dcff; border: 1px solid rgba(92,165,232,0.45); }
.prompt-mode-badge.mode-build { background: rgba(78,201,112,0.20); color: #c6efcf; border: 1px solid rgba(78,201,112,0.45); }
.prompt-mode-badge.mode-default { background: rgba(245,166,35,0.20); color: #ffdba4; border: 1px solid rgba(245,166,35,0.45); }
.prompt-mode-legend { display: flex; gap: 8px; flex-wrap: wrap; }
.prompt-mode-legend .chip { font-size: 10px; border-radius: 999px; padding: 2px 8px; border: 1px solid transparent; }
.prompt-mode-legend .chip.universal { color: #ffdba4; border-color: rgba(245,166,35,0.45); background: rgba(245,166,35,0.10); }
.prompt-mode-legend .chip.orchestrator { color: #b9dcff; border-color: rgba(92,165,232,0.45); background: rgba(92,165,232,0.10); }
.prompt-mode-legend .chip.builder { color: #c6efcf; border-color: rgba(78,201,112,0.45); background: rgba(78,201,112,0.10); }
.prompt-system-sections { display: grid; gap: 8px; padding: 10px; }
.prompt-segment { border-radius: 6px; border: 1px solid var(--border); overflow: hidden; }
.prompt-segment-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; padding: 6px 10px; border-bottom: 1px solid var(--border); }
.prompt-segment-body { padding: 10px; font-size: 12px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; max-height: 240px; overflow-y: auto; color: var(--fg); }
.prompt-segment.missing { opacity: 0.55; }
.prompt-segment.universal { border-left: 3px solid var(--accent); background: rgba(245,166,35,0.08); }
.prompt-segment.universal .prompt-segment-title { color: #ffdba4; background: rgba(245,166,35,0.12); }
.prompt-segment.orchestrator { border-left: 3px solid var(--blue); background: rgba(92,165,232,0.08); }
.prompt-segment.orchestrator .prompt-segment-title { color: #b9dcff; background: rgba(92,165,232,0.12); }
.prompt-segment.builder { border-left: 3px solid var(--green); background: rgba(78,201,112,0.08); }
.prompt-segment.builder .prompt-segment-title { color: #c6efcf; background: rgba(78,201,112,0.12); }
@media (min-width: 1200px) {
  .prompt-split { grid-template-columns: 1fr 1fr; }
}
.chain-toggle { display: inline-flex; gap: 2px; background: var(--bg4); border-radius: 3px; padding: 2px; margin-left: 8px; vertical-align: middle; }
.chain-toggle button { background: transparent; border: none; color: var(--fg2); padding: 2px 8px; border-radius: 2px; cursor: pointer; font-family: inherit; font-size: 10px; }
.chain-toggle button:hover { color: var(--fg); }
.chain-toggle button.active { background: var(--accent); color: #000; }
.chain-history-msg { margin-bottom: 8px; padding: 8px; border-radius: 4px; }
.chain-history-msg.msg-system { background: #1a2a1a; border-left: 3px solid #4a7; }
.chain-history-msg.msg-user { background: #1a1a2a; border-left: 3px solid var(--blue); }
.chain-history-msg.msg-assistant { background: #2a1a1a; border-left: 3px solid var(--accent); }
.chain-history-role { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; font-weight: bold; }
.chain-history-role.role-system { color: #4a7; }
.chain-history-role.role-user { color: var(--blue); }
.chain-history-role.role-assistant { color: var(--accent); }
.chain-block-content.response-block { color: #dcdcaa; }
.chain-block-content.exec-block { color: #b5cea8; }
.chain-divider { height: 1px; background: var(--border); margin: 4px 0 16px 0; }
</style>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <div class="sidebar-header">
      <h1>FLE VIEWER</h1>
      <div class="sub">Factorio Learning Environment</div>
    </div>
    <div class="run-list" id="runList"></div>
  </div>
  <div class="main" id="mainArea">
    <div class="placeholder">Select a run from the sidebar</div>
  </div>
</div>

<script>
let runs = [];
let currentRun = null;
let currentSteps = [];
let currentStep = 0;
let systemPrompt = '';
let viewMode = 'chain'; // 'step' or 'chain'
let promptCache = new Map();
let promptRequestSeq = 0;

function scoreColor(score) {
  if (score <= 0) return 'var(--red)';
  if (score < 100) return 'var(--accent)';
  return 'var(--green)';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

async function loadRuns() {
  const resp = await fetch('/api/runs');
  runs = await resp.json();
  renderRunList();
}

function renderRunList() {
  const el = document.getElementById('runList');
  el.innerHTML = runs.map(r => `
    <div class="run-item${currentRun && currentRun.version === r.version ? ' active' : ''}"
         onclick="selectRun(${r.version})">
      <div class="top">
        <span class="version">v${r.version}</span>
        <span class="badge badge-score">${r.max_score}</span>
      </div>
      <div class="model">${r.model}</div>
      <div class="task">${r.task}</div>
      <div class="stats">
        <span class="badge badge-steps">${r.steps} steps</span>
        ${r.has_video ? '<span class="badge badge-video">VIDEO</span>' : ''}
        <span style="color:var(--fg2)">${r.created_at ? r.created_at.split(' ')[0] : ''}</span>
      </div>
    </div>
  `).join('');
}

async function selectRun(version) {
  currentRun = runs.find(r => r.version === version);
  currentStep = 0;
  promptCache.clear();
  promptRequestSeq += 1;
  renderRunList();

  const resp = await fetch(`/api/run/${version}/steps`);
  const data = await resp.json();
  currentSteps = data.steps;
  systemPrompt = data.system_prompt || '';

  renderView();
}

function setView(mode) {
  viewMode = mode;
  renderView();
}

function renderView() {
  if (viewMode === 'chain') {
    buildChainView();
  } else {
    buildLayout();
    updateStep();
  }
}

// ── View toggle HTML ──
function viewToggleHtml() {
  return `<div class="view-toggle">
    <button class="${viewMode === 'chain' ? 'active' : ''}" onclick="setView('chain')">CHAIN</button>
    <button class="${viewMode === 'step' ? 'active' : ''}" onclick="setView('step')">STEP</button>
  </div>`;
}

// ── Chain view ──
function buildChainView() {
  if (!currentRun || !currentSteps.length) return;
  const main = document.getElementById('mainArea');
  const v = currentRun.version;

  let html = viewToggleHtml();

  // Video
  if (currentRun.has_video) {
    html += `
      <div class="video-section">
        <div class="section-header">Run Video</div>
        <video controls preload="metadata">
          <source src="/api/run/${v}/video" type="video/mp4">
        </video>
      </div>`;
  }

  html += '<div class="chain">';

  // System prompt (collapsed by default)
  if (systemPrompt) {
    html += `
      <div class="chain-system">
        <div class="chain-system-header" onclick="this.nextElementSibling.classList.toggle('open')">
          <span>System Prompt (${systemPrompt.split('\\n').length} lines)</span>
          <span>&#9662;</span>
        </div>
        <div class="chain-system-body">${escapeHtml(systemPrompt)}</div>
      </div>`;
  }

  // All steps in sequence
  for (let i = 0; i < currentSteps.length; i++) {
    const s = currentSteps[i];
    const sc = scoreColor(s.production_score);

    html += `
      <div class="chain-step${s.error ? ' has-error' : ''}" id="chain-step-${i}">
        <div class="chain-step-header">
          <span class="chain-step-num">Step ${s.step}</span>
          <span class="chain-step-score" style="background:${sc}; color:#000">${s.production_score}</span>
          ${s.error ? '<span class="chain-step-error">ERROR</span>' : ''}
          <span class="chain-step-time">${s.created_at || ''}</span>
        </div>`;

    // Exact prompt payload (lazy-loaded)
    html += `
      <div class="chain-block">
        <div class="chain-block-label">Exact Prompt Sent to LLM</div>
        <div class="chain-block-content prompt-block" id="prompt-content-${i}">
          <button class="step-btn" onclick="loadChainPrompt(${i}, ${s.step}, this)">Load exact prompt</button>
        </div>
      </div>`;

    // Full agent response (reasoning + code)
    if (s.agent_response) {
      html += `
        <div class="chain-block">
          <div class="chain-block-label">Agent Response</div>
          <div class="chain-block-content response-block">${escapeHtml(s.agent_response)}</div>
        </div>`;
    } else {
      // Fallback to just code if no conversation_json
      html += `
        <div class="chain-block">
          <div class="chain-block-label">Code</div>
          <div class="chain-block-content code-block">${escapeHtml(s.code)}</div>
        </div>`;
    }

    // Execution output (print statements)
    if (s.exec_output) {
      html += `
        <div class="chain-block">
          <div class="chain-block-label">Execution Output</div>
          <div class="chain-block-content exec-block">${escapeHtml(s.exec_output)}</div>
        </div>`;
    }

    // Screenshot if available (render after execution output)
    if (s.has_screenshot) {
      html += `
        <div class="chain-screenshot">
          <img src="/api/run/${v}/screenshot/${s.step}" onclick="this.classList.toggle('expanded')">
        </div>`;
    }

    html += '</div>'; // chain-step
    if (i < currentSteps.length - 1) html += '<div class="chain-divider"></div>';
  }

  html += '</div>'; // chain
  main.innerHTML = html;
}

// ── Step view ──
function buildLayout() {
  if (!currentRun || !currentSteps.length) return;
  const main = document.getElementById('mainArea');
  const v = currentRun.version;
  const hasScreenshots = currentRun.has_screenshots;
  const maxAbs = Math.max(1, ...currentSteps.map(s => Math.abs(s.production_score)));

  let html = viewToggleHtml();

  // Video section
  if (currentRun.has_video) {
    html += `
      <div class="video-section">
        <div class="section-header">Run Video</div>
        <video controls preload="metadata">
          <source src="/api/run/${v}/video" type="video/mp4">
        </video>
      </div>`;
  }

  // Step selector for runs without screenshots
  if (!hasScreenshots) {
    html += `
      <div class="section-header">Steps</div>
      <div class="step-selector" id="stepSelector">
        ${currentSteps.map((s, i) => `
          <button class="step-btn${s.error ? ' error' : ''}" data-idx="${i}"
                  onclick="goToStep(${i})">
            ${s.step}
          </button>
        `).join('')}
      </div>`;
  }

  // Reward timeline
  html += `
    <div class="timeline">
      <div class="timeline-label">Production Score by Step</div>
      <div class="timeline-bar" id="timelineBar">
        ${currentSteps.map((s, i) => {
          const color = scoreColor(s.production_score);
          return `<div class="timeline-seg" data-idx="${i}"
                       style="flex:1; background:${color}; opacity:${0.4 + 0.6 * (Math.abs(s.production_score) / maxAbs)}"
                       onclick="goToStep(${i})"
                       title="Step ${s.step}: ${s.production_score}">${s.production_score || ''}</div>`;
        }).join('')}
      </div>
    </div>`;

  // Code and observation panels
  html += `
    <div class="panels">
      <div class="panel">
        <div class="panel-header">
          <h3>Code</h3>
          <span class="meta" id="codeMeta"></span>
        </div>
        <div class="panel-content" id="codeContent"></div>
      </div>
      <div class="panel">
        <div class="panel-header">
          <h3>Observation</h3>
          <span class="meta" id="obsMeta"></span>
        </div>
        <div class="panel-content" id="obsContent"></div>
      </div>
    </div>`;

  html += `
    <div class="panel" style="margin-top:16px;">
      <div class="panel-header">
        <h3>Exact Prompt Sent</h3>
        <span class="meta" id="promptMeta"></span>
      </div>
      <div class="panel-content prompt-block" id="promptContent">Loading...</div>
    </div>`;

  // Screenshot section (moved below step details)
  if (hasScreenshots) {
    html += `
      <div class="screenshot-section" style="margin-top:16px;">
        <div class="section-header">Screenshots</div>
        <div class="filmstrip" id="filmstrip">
          ${currentSteps.map((s, i) => s.has_screenshot ? `
            <img class="filmstrip-thumb" data-idx="${i}"
                 src="/api/run/${v}/screenshot/${s.step}"
                 onclick="goToStep(${i})"
                 title="Step ${s.step} (score: ${s.production_score})">
          ` : '').join('')}
        </div>
        <div class="screenshot-nav">
          <button id="btnPrev" onclick="prevStep()">&#9664; Prev</button>
          <span class="step-label" id="stepLabel"></span>
          <button id="btnNext" onclick="nextStep()">Next &#9654;</button>
        </div>
        <img class="screenshot-img" id="screenshotImg" src="" style="display:none">
      </div>`;
  }

  main.innerHTML = html;
}

/** Update only the dynamic parts — no DOM rebuild, no scroll/position reset. */
function updateStep() {
  if (!currentRun || !currentSteps.length) return;
  const v = currentRun.version;
  const step = currentSteps[currentStep];
  const hasScreenshots = currentRun.has_screenshots;

  // Filmstrip active state
  document.querySelectorAll('.filmstrip-thumb').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.idx) === currentStep);
  });

  // Screenshot image
  const img = document.getElementById('screenshotImg');
  if (img) {
    if (step.has_screenshot) {
      img.src = `/api/run/${v}/screenshot/${step.step}`;
      img.style.display = '';
    } else {
      img.style.display = 'none';
    }
  }

  // Nav buttons + label
  const btnPrev = document.getElementById('btnPrev');
  const btnNext = document.getElementById('btnNext');
  const stepLabel = document.getElementById('stepLabel');
  const maxStep = currentSteps.length ? currentSteps[currentSteps.length - 1].step : 0;
  if (btnPrev) btnPrev.disabled = currentStep === 0;
  if (btnNext) btnNext.disabled = currentStep >= currentSteps.length - 1;
  if (stepLabel) {
    const suffix = (hasScreenshots && !step.has_screenshot) ? ' (no screenshot)' : '';
    stepLabel.textContent = `Step ${step.step} / ${maxStep}${suffix}`;
  }

  // Step selector buttons (non-screenshot runs)
  document.querySelectorAll('.step-btn').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.idx) === currentStep);
  });

  // Timeline active segment
  document.querySelectorAll('.timeline-seg').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.idx) === currentStep);
  });

  // Code panel
  const codeMeta = document.getElementById('codeMeta');
  const codeContent = document.getElementById('codeContent');
  if (codeMeta) {
    codeMeta.innerHTML = `Step ${step.step} &mdash; ${step.error
      ? '<span class="error-indicator">ERROR</span>'
      : '<span class="ok-indicator">OK</span>'}`;
  }
  if (codeContent) codeContent.textContent = step.code;

  // Observation panel
  const obsMeta = document.getElementById('obsMeta');
  const obsContent = document.getElementById('obsContent');
  if (obsMeta) {
    obsMeta.innerHTML = `score: <b style="color:${scoreColor(step.production_score)}">${step.production_score}</b>`;
  }
  if (obsContent) obsContent.textContent = step.observation;

  updateStepPrompt(step.step);

  // Scroll active filmstrip thumb into view
  const activeThumb = document.querySelector('.filmstrip-thumb.active');
  if (activeThumb) activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
}

function messageContentToString(content) {
  if (typeof content === 'string') return content;
  return JSON.stringify(content ?? '', null, 2);
}

function splitPromptMessages(messages) {
  const systemParts = [];
  const userParts = [];

  (messages || []).forEach((msg, idx) => {
    const role = msg.role || 'unknown';
    const content = messageContentToString(msg.content);
    if (role === 'system') {
      systemParts.push(content);
    } else {
      userParts.push(`[${idx}] ${role}\n${content}`);
    }
  });

  return {
    systemText: systemParts.length ? systemParts.join('\n\n-----\n\n') : '(no system prompt message)',
    userText: userParts.length ? userParts.join('\n\n-----\n\n') : '(no non-system prompt messages)',
  };
}

function analyzeSystemPrompt(systemText) {
  const ORCH_HEADER = '## Orchestrator Operating Mode (Fix + Connect + Delegate)';
  const BUILD_HEADER = '## Build Mode (Scoped Module Execution)';

  const idxOrch = systemText.indexOf(ORCH_HEADER);
  const idxBuild = systemText.indexOf(BUILD_HEADER);

  let mode = 'default';
  if (idxBuild >= 0) mode = 'build';
  else if (idxOrch >= 0) mode = 'orchestrator';

  const sections = [];
  const markers = [idxOrch, idxBuild].filter(i => i >= 0);
  const firstMarker = markers.length ? Math.min(...markers) : -1;

  if (firstMarker > 0) {
    const universal = systemText.slice(0, firstMarker).trim();
    if (universal) {
      sections.push({ label: 'Universal (Both Agents)', cls: 'universal', text: universal });
    }
  }

  if (idxOrch >= 0) {
    const orchEnd = (idxBuild > idxOrch) ? idxBuild : systemText.length;
    const orchestrator = systemText.slice(idxOrch, orchEnd).trim();
    if (orchestrator) {
      sections.push({ label: 'Orchestrator-Specific', cls: 'orchestrator', text: orchestrator });
    }
  }

  if (idxBuild >= 0) {
    const buildEnd = (idxOrch > idxBuild) ? idxOrch : systemText.length;
    const builder = systemText.slice(idxBuild, buildEnd).trim();
    if (builder) {
      sections.push({ label: 'Builder-Specific', cls: 'builder', text: builder });
    }
  }

  if (!sections.length) {
    sections.push({ label: 'Universal (Both Agents)', cls: 'universal', text: systemText });
  }

  return { mode, sections };
}

function renderSplitPrompt(containerEl, messages) {
  const { systemText, userText } = splitPromptMessages(messages);
  const analysis = analyzeSystemPrompt(systemText);
  const byClass = Object.fromEntries(analysis.sections.map(s => [s.cls, s]));
  const requiredSections = [
    { cls: 'universal', label: 'Universal (Both Agents)' },
    { cls: 'orchestrator', label: 'Orchestrator-Specific' },
    { cls: 'builder', label: 'Builder-Specific' },
  ];
  const sectionHtml = requiredSections.map(section => {
    const found = byClass[section.cls];
    const text = found ? found.text : '(not present in this step prompt)';
    const missingClass = found ? '' : ' missing';
    return `
    <div class="prompt-segment ${section.cls}${missingClass}">
      <div class="prompt-segment-title">${section.label}</div>
      <div class="prompt-segment-body">${escapeHtml(text)}</div>
    </div>
  `;
  }).join('');

  containerEl.innerHTML = `
    <div class="prompt-split">
      <div class="prompt-split-box">
        <div class="prompt-split-title">System Prompt (Exact)</div>
        <div class="prompt-mode-row">
          <span class="prompt-mode-badge mode-${analysis.mode}">Mode: ${analysis.mode}</span>
          <div class="prompt-mode-legend">
            <span class="chip universal">Universal</span>
            <span class="chip orchestrator">Orchestrator</span>
            <span class="chip builder">Builder</span>
          </div>
        </div>
        <div class="prompt-system-sections">${sectionHtml}</div>
      </div>
      <div class="prompt-split-box">
        <div class="prompt-split-title">User Prompt (Exact Non-System Stream)</div>
        <div class="prompt-split-body user">${escapeHtml(userText)}</div>
      </div>
    </div>`;
  return analysis;
}

async function fetchStepPrompt(stepNumber) {
  if (!currentRun) throw new Error('no run selected');
  const cacheKey = `${currentRun.version}:${stepNumber}`;
  if (promptCache.has(cacheKey)) return promptCache.get(cacheKey);

  const resp = await fetch(`/api/run/${currentRun.version}/prompt/${stepNumber}`);
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const data = await resp.json();
  promptCache.set(cacheKey, data);
  return data;
}

async function updateStepPrompt(stepNumber) {
  const contentEl = document.getElementById('promptContent');
  const metaEl = document.getElementById('promptMeta');
  if (!contentEl || !metaEl) return;

  const reqId = ++promptRequestSeq;
  contentEl.textContent = 'Loading exact prompt...';
  metaEl.textContent = '';

  try {
    const data = await fetchStepPrompt(stepNumber);
    if (reqId !== promptRequestSeq) return;
    const analysis = renderSplitPrompt(contentEl, data.messages || []);
    metaEl.textContent = `${data.message_count || 0} messages • mode: ${analysis.mode}`;
  } catch (err) {
    if (reqId !== promptRequestSeq) return;
    contentEl.textContent = `Failed to load exact prompt: ${err.message || err}`;
    metaEl.textContent = '';
  }
}

async function loadChainPrompt(stepIdx, stepNumber, btn) {
  const el = document.getElementById(`prompt-content-${stepIdx}`);
  if (!el) return;

  const oldText = btn ? btn.textContent : '';
  if (btn) btn.disabled = true;
  el.textContent = 'Loading exact prompt...';

  try {
    const data = await fetchStepPrompt(stepNumber);
    renderSplitPrompt(el, data.messages || []);
  } catch (err) {
    el.textContent = `Failed to load exact prompt: ${err.message || err}`;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = oldText || 'Load exact prompt';
    }
  }
}

function goToStep(i) {
  currentStep = i;
  if (viewMode === 'chain') {
    const el = document.getElementById(`chain-step-${i}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else {
    updateStep();
  }
}

function prevStep() {
  if (currentStep > 0) goToStep(currentStep - 1);
}

function nextStep() {
  if (currentStep < currentSteps.length - 1) goToStep(currentStep + 1);
}

// Keyboard navigation
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft') prevStep();
  else if (e.key === 'ArrowRight') nextStep();
});

loadRuns();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return HTML


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="FLE Trajectory Viewer")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(f"FLE Viewer: http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=True)
