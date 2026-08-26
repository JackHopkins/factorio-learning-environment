import asyncio
from datetime import datetime, timedelta, timezone
import json
import subprocess
from types import SimpleNamespace

import pytest

from fle.envd.benchmark import BENCHMARK_VERSION, get_benchmark_task
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    build_capability_ladder,
    summarize_run,
)
from scripts import hermes_benchmark

pytestmark = pytest.mark.no_factorio


def _args(**overrides):
    values = {
        "reasoning": "low",
        "timeout_seconds": 10.0,
        "max_turns": 4,
        "envd_url": "http://127.0.0.1:8172",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _attempt(task, *, success=True, status="completed", index=0, reward=1.0, **extra):
    return BenchmarkAttempt(
        task_id=task.task_id,
        task_fingerprint=task.task_spec.fingerprint,
        attempt=index,
        seed=task.task_spec.seed,
        success=success,
        scalar_reward=reward,
        interventions=1,
        elapsed_seconds=1,
        status=status,
        **extra,
    )


def _run(run_id, model, attempts, **run_overrides):
    task = get_benchmark_task("micro_place_lab_v1")
    started = datetime(2026, 8, 23, tzinfo=timezone.utc)
    values = {
        "run_id": run_id,
        "benchmark_version": BENCHMARK_VERSION,
        "model": ModelIdentity(name=model, provider="test"),
        "suite": "api_microtasks_v1",
        "benchmark_split": "development",
        "started_at": started,
        "completed_at": started + timedelta(seconds=1),
        "repository_commit": "a" * 40,
        "attempts": attempts,
    }
    values.update(run_overrides)
    return BenchmarkRun(**values)


def test_prompt_uses_canonical_task_builder_reference():
    spec = get_benchmark_task("micro_place_lab_v1").task_spec
    prompt = hermes_benchmark.build_prompt(spec)

    assert "mcp__factorio__factorio_observe_factory" in prompt
    assert "mcp__factorio__factorio_execute_program" in prompt
    assert "get_prototype_recipe" in prompt
    assert "RecipeName.X" in prompt
    assert "Do not import FLE or use reflection" in prompt
    assert "--max-turns" not in prompt


def test_profile_isolated_and_allowlists_only_factorio(tmp_path):
    profile = tmp_path / "profile"
    scratch = tmp_path / "scratch"
    trace = scratch / "trace.log"
    hermes_benchmark._write_hermes_profile(
        profile, scratch, "http://envd", "lease-123", trace, max_turns=7
    )

    import json

    config = json.loads((profile / "config.yaml").read_text(encoding="utf-8"))
    assert config["platform_toolsets"] == {"cli": ["factorio"]}
    assert list(config["mcp_servers"]) == ["factorio"]
    assert config["mcp_servers"]["factorio"]["env"]["LEASE_ID"] == "lease-123"
    assert config["agent"]["api_max_retries"] == 3
    assert "web" in config["agent"]["disabled_toolsets"]
    assert "web" not in config["platform_toolsets"]["cli"]
    assert "terminal" not in config["platform_toolsets"]["cli"]


def test_contract_profile_has_no_turn_budget(tmp_path):
    import json

    from fle.envd.models import (
        CustomerContractSpec,
        DemandOrderSpec,
        FactorioTaskSpec,
        ProductDemandSpec,
    )

    spec = FactorioTaskSpec(
        task_id="customer",
        goal="fulfil",
        customer=CustomerContractSpec(
            orders=[
                DemandOrderSpec(
                    order_id="one",
                    products=[ProductDemandSpec(product="iron-plate", quantity=1)],
                    issue_tick=0,
                    due_tick=100,
                )
            ]
        ),
    )
    assert hermes_benchmark._effective_max_turns(spec, 24) is None

    profile = tmp_path / "profile"
    scratch = tmp_path / "scratch"
    hermes_benchmark._write_hermes_profile(
        profile,
        scratch,
        "http://envd",
        "lease-123",
        scratch / "trace.log",
        max_turns=None,
    )
    config = json.loads((profile / "config.yaml").read_text(encoding="utf-8"))
    assert config["agent"]["max_turns"] is None


def test_profile_passes_epoch_terminal_signal_to_mcp(tmp_path):
    profile = tmp_path / "profile"
    scratch = tmp_path / "scratch"
    terminal = tmp_path / "terminal.json"
    hermes_benchmark._write_hermes_profile(
        profile,
        scratch,
        "http://envd",
        "lease-123",
        scratch / "trace.log",
        max_turns=None,
        terminal_file=terminal,
        api_max_retries=12,
    )
    config = json.loads((profile / "config.yaml").read_text(encoding="utf-8"))
    assert config["mcp_servers"]["factorio"]["env"]["MCP_TERMINAL_FILE"] == str(
        terminal
    )
    assert config["agent"]["api_max_retries"] == 12


def test_profile_can_enable_compaction_for_persistent_sessions(tmp_path):
    profile = tmp_path / "profile"
    scratch = tmp_path / "scratch"
    hermes_benchmark._write_hermes_profile(
        profile,
        scratch,
        "http://envd",
        "lease-123",
        scratch / "trace.log",
        max_turns=None,
        compression_enabled=True,
    )
    config = json.loads((profile / "config.yaml").read_text(encoding="utf-8"))
    assert config["compression"] == {"enabled": True, "threshold": 0.50}


def test_usage_fallback_does_not_double_count_json_and_hit_rate_is_bounded(tmp_path):
    output = '{"input_tokens": 100, "cache_read_tokens": 25}\n'
    usage = hermes_benchmark._extract_usage(output)
    assert usage["input_tokens"] == 100
    assert usage["cached_tokens"] == 25
    assert hermes_benchmark._cache_hit_rate(usage) == pytest.approx(0.2)
    assert (
        hermes_benchmark._cache_hit_rate({"input_tokens": 1, "cached_tokens": 99}) <= 1
    )


def test_nonzero_exit_classifies_provider_and_parser_failures():
    assert hermes_benchmark._classify_nonzero_exit(1, "HTTP 429 quota exceeded")[0] == (
        "provider_quota"
    )
    assert hermes_benchmark._classify_nonzero_exit(2, "invalid JSON tool call")[0] == (
        "parser_error"
    )


def test_success_exit_still_classifies_provider_and_raw_tool_call_failures():
    quota = "API call failed after 3 retries: HTTP 429 free-models-per-day"
    assert hermes_benchmark._classify_output_failure(quota) == (
        "provider_quota",
        "provider quota or rate limit",
    )
    raw_call = '{"name":"tool_call","args":{"arguments":{"code":"print(1)"}}}'
    assert hermes_benchmark._classify_output_failure(raw_call) == (
        "parser_error",
        "model tool call was returned as assistant text",
    )
    empty_reply = "No reply: the model returned empty content after retries"
    assert hermes_benchmark._classify_output_failure(empty_reply) == (
        "provider_error",
        "provider or transport error",
    )


def test_hermes_uses_one_shot_usage_file_and_isolated_home(monkeypatch, tmp_path):
    calls = {}

    class Process:
        pid = 321
        returncode = 0
        stdout = None
        stderr = None

        def communicate(self, timeout=None):
            return "final response", ""

        def poll(self):
            return self.returncode

    def fake_popen(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(hermes_benchmark.subprocess, "Popen", fake_popen)
    profile = tmp_path / "profile"
    scratch = tmp_path / "scratch"
    usage = scratch / "usage.json"
    invocation = hermes_benchmark._run_hermes(
        profile, scratch, usage, "prompt", "provider/model", _args()
    )

    assert invocation.failure_category is None
    assert "-z" in calls["command"]
    assert "--usage-file" in calls["command"]
    assert "--toolsets" in calls["command"]
    assert "factorio" in calls["command"]
    assert calls["kwargs"]["env"]["HERMES_HOME"] == str(profile)


def test_hermes_can_resume_latest_isolated_session(monkeypatch, tmp_path):
    calls = {}

    class Process:
        pid = 321
        returncode = 0
        stdout = None
        stderr = None

        def communicate(self, timeout=None):
            return "continued", ""

    def fake_popen(command, **kwargs):
        calls["command"] = command
        return Process()

    monkeypatch.setattr(hermes_benchmark.subprocess, "Popen", fake_popen)
    scratch = tmp_path / "scratch"
    invocation = hermes_benchmark._run_hermes(
        tmp_path / "profile",
        scratch,
        scratch / "usage.json",
        "next order",
        "stealth/ox-alpha",
        _args(),
        resume_latest=True,
    )

    assert invocation.failure_category is None
    assert calls["command"][calls["command"].index("--resume") + 1] == "latest"
    assert calls["command"][calls["command"].index("--in") + 1] == str(scratch)
    assert calls["command"][calls["command"].index("--toolsets") + 1] == "factorio"


def test_hermes_timeout_terminates_the_process_tree(monkeypatch, tmp_path):
    calls = {"communicate": 0, "terminated": False}

    class Process:
        pid = 321
        returncode = -9

        def communicate(self, timeout=None):
            calls["communicate"] += 1
            if calls["communicate"] == 1:
                raise subprocess.TimeoutExpired("hermes", timeout, output="partial")
            return "", ""

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        hermes_benchmark.subprocess, "Popen", lambda command, **kwargs: Process()
    )
    monkeypatch.setattr(
        hermes_benchmark,
        "_terminate_process_tree",
        lambda process: calls.update(terminated=True),
    )

    invocation = hermes_benchmark._run_hermes(
        tmp_path / "profile",
        tmp_path,
        tmp_path / "usage.json",
        "prompt",
        "provider/model",
        _args(timeout_seconds=0.01),
    )

    assert calls["terminated"] is True
    assert invocation.failure_category == "timeout"
    assert "partial" in invocation.output


def test_harness_failures_are_excluded_from_summary_and_ladder():
    task = get_benchmark_task("micro_place_lab_v1")
    run = _run(
        "failed",
        "model",
        [
            _attempt(task, success=True),
            _attempt(
                task,
                success=False,
                status="infrastructure_failure",
                index=1,
                reward=0,
                failure_category="provider_quota",
            ),
        ],
    )
    summary = summarize_run(run)
    assert summary["attempt_count"] == 1
    assert summary["recorded_attempt_count"] == 2
    assert summary["excluded_attempt_count"] == 1
    assert summary["success_rate"] == 1
    assert summary["failure_counts"] == {"provider_quota": 1}
    ladder = build_capability_ladder([run])
    row = ladder["ladder"][0]
    assert row["attempt_count"] == 1
    assert row["excluded_attempt_count"] == 1


def test_ladder_does_not_pair_incompatible_generation_conditions():
    task = get_benchmark_task("micro_place_lab_v1")
    first = _run("first", "alpha", [_attempt(task, reward=1.0)])
    second = _run(
        "second",
        "beta",
        [_attempt(task, reward=0.0)],
        generation_config={"harness": "hermes-agent", "reasoning": "high"},
    )
    ladder = build_capability_ladder([first, second])
    assert ladder["game_count"] == 0
    rows = {row["model_key"]: row for row in ladder["ladder"]}
    assert rows["test/alpha"]["elo"] == 1200.0
    assert rows["test/beta"]["elo"] == 1200.0


def test_ladder_does_not_pair_unequal_attempt_plans():
    task = get_benchmark_task("micro_place_lab_v1")
    first = _run("first", "alpha", [_attempt(task, index=0, reward=1.0)])
    second = _run(
        "second",
        "beta",
        [
            _attempt(task, index=0, reward=0.0),
            _attempt(task, index=1, reward=0.0),
        ],
    )
    ladder = build_capability_ladder([first, second])
    assert ladder["game_count"] == 0


def test_hermes_writes_one_run_and_summary_per_model(monkeypatch, tmp_path):
    async def fake_run_attempt(model, task_id, attempt_index, args):
        task = get_benchmark_task(task_id)
        return _attempt(task), {"model": model, "task_id": task_id}

    monkeypatch.setattr(hermes_benchmark, "run_attempt", fake_run_attempt)
    args = SimpleNamespace(
        models="test/alpha,test/beta",
        task_id=["micro_place_lab_v1"],
        attempts=1,
        max_turns=2,
        timeout_seconds=1.0,
        envd_url="http://envd",
        output_dir=str(tmp_path),
        reasoning="low",
    )

    asyncio.run(hermes_benchmark.main_async(args))

    for model in ("alpha", "beta"):
        assert (tmp_path / f"{model}-run.json").exists()
        assert (tmp_path / f"{model}-details.json").exists()
        assert (tmp_path / f"{model}-summary.json").exists()


def test_ladder_excludes_only_the_task_with_an_infrastructure_failure():
    lab = get_benchmark_task("micro_place_lab_v1")
    gear = get_benchmark_task("micro_craft_iron_gear_v1")
    first = _run(
        "first",
        "alpha",
        [
            _attempt(lab, index=0, reward=1.0),
            _attempt(
                gear,
                index=0,
                success=False,
                status="infrastructure_failure",
                reward=0.0,
                failure_category="provider_quota",
            ),
        ],
    )
    second = _run(
        "second",
        "beta",
        [_attempt(lab, index=0, reward=0.0), _attempt(gear, index=0, reward=0.0)],
    )

    ladder = build_capability_ladder([first, second])
    assert ladder["game_count"] == 1
