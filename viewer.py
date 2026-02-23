#!/usr/bin/env python
"""
FLE Trajectory Viewer — browse agent runs, screenshots, and videos.

Usage:
    python viewer.py          # serves on http://localhost:5050
    python viewer.py --port 8080
"""

import json
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
        "FROM programs WHERE version=? ORDER BY depth",
        (version,),
    ).fetchall()

    # Read system prompt if available
    sys_prompt_file = TRAJ_DIR / f"v{version}" / "agent0_system_prompt.txt"
    system_prompt = sys_prompt_file.read_text() if sys_prompt_file.is_file() else ""

    steps = []
    for r in rows:
        step = int(r["depth"])
        meta = json.loads(r["meta"]) if r["meta"] else {}

        # Read observation from trajectory log
        obs_file = TRAJ_DIR / f"v{version}" / f"agent0_iter{step}_observation.txt"
        observation = obs_file.read_text() if obs_file.is_file() else ""

        # Check screenshot
        screen_path = SCREEN_DIR / f"v{version}" / f"step_{step:03d}.png"

        # Extract user prompt from conversation_json.
        # At depth N, conversation has: [system, user0, asst0, user1, asst1, ..., userN]
        # So depth N has the assistant response for step N-1 but NOT for step N.
        user_prompt = ""
        if r["conversation_json"]:
            try:
                msgs = json.loads(r["conversation_json"]).get("messages", [])
                user_idx = 2 * step + 1
                if user_idx < len(msgs) and msgs[user_idx]["role"] == "user":
                    user_prompt = msgs[user_idx]["content"]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        steps.append({
            "step": step,
            "reward": round(r["value"], 2),
            "production_score": meta.get("production_score", 0),
            "error": meta.get("error_occurred", False),
            "code": r["code"] or "",
            "observation": observation,
            "agent_response": "",
            "user_prompt": user_prompt,
            "exec_output": r["response"] or "",
            "has_screenshot": screen_path.is_file(),
            "created_at": r["created_at"],
            "_conversation_json": r["conversation_json"],
        })

    # Second pass: extract agent responses from the NEXT row's conversation
    for i, s in enumerate(steps):
        next_conv = steps[i + 1]["_conversation_json"] if i + 1 < len(steps) else None
        src = next_conv or s["_conversation_json"]
        if src:
            try:
                msgs = json.loads(src).get("messages", [])
                asst_idx = 2 * s["step"] + 2
                if asst_idx < len(msgs) and msgs[asst_idx]["role"] == "assistant":
                    s["agent_response"] = msgs[asst_idx]["content"]
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        del s["_conversation_json"]

    conn.close()
    return jsonify({"system_prompt": system_prompt, "steps": steps})


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

    // Screenshot if available
    if (s.has_screenshot) {
      html += `
        <div class="chain-screenshot">
          <img src="/api/run/${v}/screenshot/${s.step}" onclick="this.classList.toggle('expanded')">
        </div>`;
    }

    // Prompt with chain toggle
    if (s.user_prompt) {
      html += `
        <div class="chain-block">
          <div class="chain-block-label">Prompt
            <span class="chain-toggle">
              <button class="active" onclick="showPromptMode(${i}, 'single', this)">This step</button>
              <button onclick="showPromptMode(${i}, 'chain', this)">Full chain</button>
            </span>
          </div>
          <div class="chain-block-content prompt-block" id="prompt-content-${i}">${escapeHtml(s.user_prompt)}</div>
        </div>`;
    }

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

  // Screenshot section or step selector
  if (hasScreenshots) {
    html += `
      <div class="screenshot-section">
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
  } else {
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
  if (btnPrev) btnPrev.disabled = currentStep === 0;
  if (btnNext) btnNext.disabled = currentStep >= currentSteps.length - 1;
  if (stepLabel) {
    const suffix = (hasScreenshots && !step.has_screenshot) ? ' (no screenshot)' : '';
    stepLabel.textContent = `Step ${step.step} / ${currentSteps.length - 1}${suffix}`;
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

  // Scroll active filmstrip thumb into view
  const activeThumb = document.querySelector('.filmstrip-thumb.active');
  if (activeThumb) activeThumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
}

function showPromptMode(stepIdx, mode, btn) {
  // Toggle active state on buttons
  const toggle = btn.parentElement;
  toggle.querySelectorAll('button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  const el = document.getElementById(`prompt-content-${stepIdx}`);
  if (!el) return;

  if (mode === 'single') {
    el.innerHTML = escapeHtml(currentSteps[stepIdx].user_prompt);
    el.className = 'chain-block-content prompt-block';
    return;
  }

  // Full chain: build all messages up to and including this step's prompt
  let html = '';

  // System prompt (truncated preview)
  if (systemPrompt) {
    const preview = systemPrompt.length > 500
      ? systemPrompt.slice(0, 500) + '\n... (' + systemPrompt.length + ' chars total)'
      : systemPrompt;
    html += `<div class="chain-history-msg msg-system">
      <div class="chain-history-role role-system">System</div>
      ${escapeHtml(preview)}
    </div>`;
  }

  // Previous steps: user prompt + agent response
  for (let j = 0; j <= stepIdx; j++) {
    const st = currentSteps[j];
    if (st.user_prompt) {
      html += `<div class="chain-history-msg msg-user">
        <div class="chain-history-role role-user">User (step ${st.step})</div>
        ${escapeHtml(st.user_prompt)}
      </div>`;
    }
    if (j < stepIdx && st.agent_response) {
      html += `<div class="chain-history-msg msg-assistant">
        <div class="chain-history-role role-assistant">Assistant (step ${st.step})</div>
        ${escapeHtml(st.agent_response)}
      </div>`;
    }
  }

  el.innerHTML = html;
  el.className = 'chain-block-content';
  el.style.maxHeight = '600px';
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
