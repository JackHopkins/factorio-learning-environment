"""Runner tests: pure helpers plus an end-to-end loop over a fake envd client.

The end-to-end test exercises the full persistent-session policy -- context
capture, candidate generation, seeded selection, commitment, begin/finalize,
outcome mapping, TrueSkill updates, atomic persistence, and the stopping
rule -- without any HTTP or Factorio dependency.
"""

import json
from types import SimpleNamespace

import pytest

from fle.envd.contract_features import ProductCatalog, StaticRecipeDataSource
from fle.envd.models import (
    CapabilityRating,
    ContractEpochOutcome,
    ContractEpochSpec,
)

pytestmark = pytest.mark.no_factorio


import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.adaptive_contract_benchmark import (  # noqa: E402
    CUSTOMER_DEPOT_LOCATION,
    OpenAICompatibleAgentSession,
    OpenCodePersistentAgentSession,
    ScriptedAgentSession,
    _load_recipe_dump,
    _refresh_coverage_obligations,
    build_candidate_pool,
    freeplay_task_spec,
    render_order_prompt,
    run_session,
    stopping_rule_met,
    _selection_seed,
)


RECIPES = [
    {
        "name": name,
        "category": category,
        "energy": energy,
        "ingredients": ingredients,
        "products": [{"name": name, "amount": 1}],
        "enabled": enabled,
    }
    for name, category, energy, ingredients, enabled in [
        ("iron-plate", "smelting", 3.2, [{"name": "iron-ore", "amount": 1}], True),
        ("copper-plate", "smelting", 3.2, [{"name": "copper-ore", "amount": 1}], True),
        ("stone-brick", "smelting", 3.2, [{"name": "stone", "amount": 2}], True),
    ]
]


def _catalog() -> ProductCatalog:
    return ProductCatalog(StaticRecipeDataSource(RECIPES))


def _context(epoch_index: int = 0):
    from fle.envd.models import ContractContextSnapshot

    return ContractContextSnapshot(
        session_id="s",
        epoch_index=epoch_index,
        captured_tick=1000 * epoch_index,
        technology_ids=("electricity",),
        unlocked_recipe_ids=(),
        inventory_counts={},
        placed_entity_counts={"stone-furnace": 4},
        production_rates_60s={},
        production_rates_300s={},
        power_capacity_kw=300.0,
        power_utilization=0.2,
        logistic_network_count=0,
        train_stop_count=0,
        pollution_total=None,
        evolution_factor=None,
        map_seed_hash="msh",
        state_digest="digest",
    )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_freeplay_task_is_persistent_open_play():
    spec = freeplay_task_spec()
    assert spec.task_family == "open_play"
    assert spec.adaptive_contract_session is True
    assert spec.objectives == []
    assert spec.verifier.implementation == "objective_engine_v1"


def test_opencode_session_writes_isolated_factorio_config(tmp_path):
    session = OpenCodePersistentAgentSession(
        envd_url="http://127.0.0.1:8172",
        lease_id="lease-test",
        model="opencode/muse-spark-1.2-contributor-free",
        reasoning="max",
        timeout_seconds=60,
        artifacts_dir=tmp_path / "artifacts",
        command=sys.executable,
    )
    try:
        config = json.loads((session.scratch / "opencode.json").read_text())
        assert config["default_agent"] == "factorio-eval"
        assert config["compaction"] == {"auto": True, "prune": True}
        assert config["agent"]["factorio-eval"]["permission"] == {
            "*": "deny",
            "factorio_*": "allow",
        }
        factorio = config["mcp"]["factorio"]
        assert factorio["environment"]["LEASE_ID"] == "lease-test"
        assert factorio["command"][1].endswith("factorio_codex_mcp.py")
        assert session.variant == "xhigh"
    finally:
        session._scratch.cleanup()


def test_opencode_session_id_parses_json_event_stream():
    output = "noise\n" + json.dumps({"type": "step_start", "sessionID": "ses_123"})
    assert OpenCodePersistentAgentSession._parse_session_id(output) == "ses_123"


def test_render_order_prompt_contains_commitment_relevant_facts():
    from tests.envd.test_adaptive_contract_backend import _spec

    spec = _spec(1)
    prompt = render_order_prompt(spec)
    assert spec.item_name in prompt
    assert str(spec.quantity) in prompt
    assert str(spec.deadline_ticks) in prompt
    assert CUSTOMER_DEPOT_LOCATION in prompt


def test_openai_tool_manifest_is_flat_and_model_time_excludes_tools(monkeypatch):
    """The provider receives one tool schema list, not a nested list."""

    class _Completions:
        def __init__(self):
            self.calls = []
            self.responses = [
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content="",
                                tool_calls=[
                                    SimpleNamespace(
                                        id="call-1",
                                        function=SimpleNamespace(
                                            name="submit_program",
                                            arguments=json.dumps({"code": "build"}),
                                        ),
                                    )
                                ],
                            )
                        )
                    ]
                ),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="done", tool_calls=None)
                        )
                    ]
                ),
            ]

        async def create(self, **kwargs):
            import asyncio

            self.calls.append(kwargs)
            await asyncio.sleep(0.001)
            return self.responses.pop(0)

    completions = _Completions()
    session = object.__new__(OpenAICompatibleAgentSession)
    session._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    session.model = "test-model"
    session.temperature = 0.0
    session.max_turns = 2
    session.messages = []

    async def execute(_code, *, request_id=None):
        import asyncio

        await asyncio.sleep(0.01)
        return "ok"

    session._executor = execute
    import asyncio
    import scripts.adaptive_contract_benchmark as adaptive_runner

    clock = iter((0.0, 2.0, 12.0, 20.0))
    monkeypatch.setattr(adaptive_runner.time, "perf_counter", lambda: next(clock))
    telemetry = asyncio.run(session.run_epoch("order"))

    assert completions.calls
    assert all(call["tools"] == session.TOOL_MANIFEST for call in completions.calls)
    assert all(not isinstance(call["tools"][0], list) for call in completions.calls)
    assert telemetry.tool_seconds == pytest.approx(10.0)
    assert telemetry.model_seconds == pytest.approx(10.0)


def test_recipe_dump_requires_existing_nonempty_authoritative_data(tmp_path):
    with pytest.raises(ValueError, match="non-empty recipe dump"):
        _load_recipe_dump(None)

    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty JSON list"):
        _load_recipe_dump(str(empty))

    malformed = tmp_path / "malformed.json"
    malformed.write_text(json.dumps([{"category": "smelting"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="without a non-empty name"):
        _load_recipe_dump(str(malformed))


def test_recipe_dump_loads_research_unlock_metadata(tmp_path):
    dump = tmp_path / "game-data.json"
    dump.write_text(
        json.dumps(
            {
                "recipes": RECIPES
                + [
                    {
                        "name": "steel-plate",
                        "category": "smelting",
                        "ingredients": [{"name": "iron-plate", "amount": 5}],
                        "products": [{"name": "steel-plate", "amount": 1}],
                        "enabled": False,
                    }
                ],
                "technologies": [
                    {
                        "name": "steel-processing",
                        "unlocked_recipes": ["steel-plate"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    recipes, technologies = _load_recipe_dump(str(dump))
    catalog = ProductCatalog(StaticRecipeDataSource(recipes, technologies))

    assert catalog.require("steel-plate").recipe.enabled is False
    assert catalog.enabling_technologies("steel-plate") == frozenset(
        {"steel-processing"}
    )


def test_coverage_obligations_refresh_with_reachable_frontier():
    from fle.envd.contract_selector import SelectionHistory

    history = SelectionHistory()
    required_bands, required_mixtures = _refresh_coverage_obligations(
        required_bands=set(),
        required_mixtures=set(),
        reachable_bands={1, 2},
        reachable_mixtures={"consolidation", "frontier"},
        history=history,
    )
    assert required_bands == {1, 2}
    assert required_mixtures == {"consolidation", "frontier"}

    history.record(_features_for_test_band(1), "consolidation")
    required_bands, required_mixtures = _refresh_coverage_obligations(
        required_bands=required_bands,
        required_mixtures=required_mixtures,
        reachable_bands={2, 3},
        reachable_mixtures={"frontier", "stress"},
        history=history,
    )
    # Band 1 and consolidation are exhausted from the current frontier;
    # newly reachable band 3 and stress are added without an impossible gate.
    assert required_bands == {2, 3}
    assert required_mixtures == {"frontier", "stress"}


def _features_for_test_band(stage_band: int):
    from fle.envd.models import ContractDifficultyFeatures

    return ContractDifficultyFeatures(
        product_id="iron-plate",
        product_tier=0,
        recipe_depth=1,
        missing_technology_count=0,
        missing_machine_type_count=0,
        required_new_intermediate_count=0,
        log_quantity=1.0,
        deadline_ticks=3600,
        required_rate_per_minute=1.0,
        existing_rate_per_minute=1.0,
        inventory_coverage_ratio=0.0,
        estimated_power_fraction=0.0,
        transport_complexity=0.0,
        stage_band=stage_band,
    )


def test_selection_seed_is_deterministic_and_epoch_sensitive():
    assert _selection_seed("run", 0, 7) == _selection_seed("run", 0, 7)
    assert _selection_seed("run", 0, 7) != _selection_seed("run", 1, 7)
    assert _selection_seed("run", 0, 7) != _selection_seed("other", 0, 7)


def test_stopping_rule_requires_coverage_gate():
    rating = CapabilityRating(
        model_version="m",
        mu=0.0,
        sigma=0.1,
        conservative_score=-0.3,
        rated_epoch_count=50,
    )
    from fle.envd.models import SessionStoppingConfig

    config = SessionStoppingConfig(
        target_sigma=1.0,
        max_rated_epochs=60,
        max_session_ticks=2_000,
    )
    # Sigma trigger satisfied but coverage gate open -> keep going.
    assert not stopping_rule_met(
        rating, 5, 1000, 10, mandatory_coverage_complete=False, config=config
    )
    assert stopping_rule_met(
        rating, 5, 1000, 10, mandatory_coverage_complete=True, config=config
    )
    # Tick trigger.
    assert stopping_rule_met(
        rating,
        5,
        config.max_session_ticks + 1,
        0,
        mandatory_coverage_complete=True,
        config=config,
    )


def test_default_stopping_policy_has_no_evaluation_budgets():
    from fle.envd.models import SessionStoppingConfig

    config = SessionStoppingConfig()
    assert config.target_sigma is None
    assert config.max_rated_epochs is None
    assert config.max_session_ticks is None
    assert config.max_session_interventions is None
    assert config.max_failed_deliveries == 5
    assert config.wall_clock_failsafe_seconds == 24 * 3600


def test_failed_deliveries_and_wall_clock_bypass_coverage_gate():
    from fle.envd.models import SessionStoppingConfig

    rating = CapabilityRating(
        model_version="m",
        mu=0.0,
        sigma=2.0,
        conservative_score=-6.0,
        rated_epoch_count=0,
    )
    config = SessionStoppingConfig(
        max_failed_deliveries=3,
        wall_clock_failsafe_seconds=100.0,
    )
    assert stopping_rule_met(
        rating,
        2,
        10,
        50_000,
        mandatory_coverage_complete=False,
        config=config,
        failed_deliveries=3,
    )
    assert stopping_rule_met(
        rating,
        2,
        10,
        50_000,
        mandatory_coverage_complete=False,
        config=config,
        wall_seconds=100.0,
    )


def test_scripted_agent_records_prompts_and_one_conversation():
    agent = ScriptedAgentSession(responses=["a", "b"])

    class _Loop:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    import asyncio

    async def drive():
        await agent.start("system")
        first = await agent.run_epoch("order-1")
        second = await agent.run_epoch("order-2")
        await agent.close()
        return first, second

    first, second = asyncio.run(drive())
    assert agent.system_prompt == "system"
    assert agent.prompts == ["order-1", "order-2"]
    assert first.turns == 1 and second.turns == 1
    assert agent.closed


def test_candidate_pool_builds_from_static_catalog():
    pool = build_candidate_pool(
        context=_context(),
        catalog=_catalog(),
        difficulty_model=_DefaultModel(),
        selection_history=__import__(
            "fle.envd.contract_selector", fromlist=["SelectionHistory"]
        ).SelectionHistory(),
        remaining_session_ticks=None,
        calibration_manifest=None,
        pool_size_per_template=2,
    )
    assert pool
    accepted = [c for c in pool if c.accepted]
    assert accepted
    assert all(c.features is not None for c in accepted)


class _DefaultModel:
    def evaluate(self, features):
        return (2.0, 0.5, 1.5)


# ---------------------------------------------------------------------------
# End-to-end session loop over a fake client
# ---------------------------------------------------------------------------


class FakeClient:
    """Scripted stand-in for HTTPEnvironmentClient.

    The scripted agent 'delivers' every order fully on its first epoch, so
    the runner should rate wins until the stopping rule closes the session.
    """

    def __init__(self, max_epochs: int = 4):
        self.max_epochs = max_epochs
        self.begun: list[int] = []
        self.finalized: list[ContractEpochOutcome] = []
        self.executed_programs: list[str] = []
        self.released = False
        self._lease_id = "lease-fake"
        self.session_id: str | None = None

        from datetime import datetime, timezone

        self.started = datetime.now(timezone.utc)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def lease(self, task, **kwargs):
        from fle.envd.models import Lease

        return Lease(
            lease_id=self._lease_id,
            worker_id="worker-fake",
            task=task,
            initial_state_hash="h",
            created_at=self.started,
            expires_at=self.started.replace(year=self.started.year + 1),
        )

    async def execute(self, lease_id: str, code: str):
        from fle.envd.models import ActionEvent, ExecutionResult

        self.executed_programs.append(code)
        return ExecutionResult(
            lease_id=lease_id,
            event=ActionEvent(
                sequence=len(self.executed_programs),
                code_sha256="x" * 64,
                started_at=self.started,
                duration_seconds=0.01,
                result="ok",
            ),
            production_score=1.0,
            automated_production_score=1.0,
            state_hash="state",
        )

    async def capture_contract_context(
        self, lease_id: str, session_id: str, epoch_index: int
    ):
        return _context(epoch_index)

    async def begin_contract_epoch(
        self, lease_id: str, spec: ContractEpochSpec, *, request_id=None
    ):
        self.begun.append(spec.epoch_index)
        self.session_id = spec.session_id
        from fle.envd.models import (
            ActiveContractState,
            OpenContractView,
            ProductDemandSpec,
        )

        return ActiveContractState(
            lease_id=lease_id,
            session_id=spec.session_id,
            epoch_index=spec.epoch_index,
            spec_commitment_hash=spec.commitment_hash,
            open_order=OpenContractView(
                order_id="epoch-order",
                kind="one_shot",
                products=[
                    ProductDemandSpec(
                        product=spec.item_name, quantity=float(spec.quantity)
                    )
                ],
                issued_at_tick=0,
                due_tick=spec.deadline_ticks,
                status="open",
            ),
            epoch_start_tick=0,
        )

    async def finalize_contract_epoch(
        self,
        lease_id: str,
        epoch_index: int,
        commitment_hash: str,
        *,
        abandon=False,
        infrastructure_interrupt=False,
        request_id=None,
    ) -> ContractEpochOutcome:
        outcome = ContractEpochOutcome(
            session_id=self.session_id or "adaptive-fake",
            epoch_index=epoch_index,
            commitment_hash=commitment_hash,
            status="infrastructure_error"
            if infrastructure_interrupt
            else ("abandoned" if abandon else "fulfilled"),
            delivered_quantity=0,
            requested_quantity=100,
            completion_ratio=1.0 if not (abandon or infrastructure_interrupt) else 0.0,
            simulation_ticks_used=36000 * epoch_index,
            interventions_used=2,
            model_seconds=0.5,
            tool_seconds=0.25,
            runner_wall_seconds=1.0,
            first_delivery_tick=600,
            completion_tick=30000,
            terminal_state_digest="terminal",
        )
        self.finalized.append(outcome)
        return outcome

    async def get_contract_session_state(self, lease_id: str):
        from fle.envd.models import ContractSessionState

        return ContractSessionState(
            lease_id=lease_id,
            session_id=self.session_id or "adaptive-fake",
            session_simulation_ticks=36000 * len(self.begun),
            epoch_simulation_ticks=0,
            completed_epoch_count=len(self.finalized),
            active_epoch_index=None,
            active_commitment_hash=None,
            agent_interventions=2 * len(self.begun),
        )

    async def finalize_contract_session(self, lease_id: str):
        from fle.envd.models import ContractSessionSummary

        return ContractSessionSummary(
            session_id=self.session_id or "adaptive-fake",
            session_simulation_ticks=36000 * len(self.begun),
            epochs=list(self.finalized),
            fulfilled_epochs=sum(o.status == "fulfilled" for o in self.finalized),
            total_delivered=sum(o.delivered_quantity for o in self.finalized),
            total_requested=sum(o.requested_quantity for o in self.finalized),
        )

    async def release(self, lease_id: str) -> None:
        self.released = True


@pytest.fixture
def fake_client_factory(monkeypatch):
    holder = {}

    def install(max_epochs: int = 4) -> FakeClient:
        client = FakeClient(max_epochs=max_epochs)
        holder["client"] = client

        import scripts.adaptive_contract_benchmark as runner

        def factory(url):
            return client

        monkeypatch.setattr(runner, "HTTPEnvironmentClient", factory)
        return client

    return install


def _args(tmp_path, **overrides):
    defaults = {
        "run_id": "runner-test",
        "seed": 3,
        "output": tmp_path / "session.json",
        "recipe_dump": _write_recipe_dump(tmp_path),
        "calibration_manifest": None,
        "scripted_responses": json.dumps(["build"]),
        "wall_clock_failsafe_seconds": 30.0,
        "max_turns_per_epoch": 2,
        "target_sigma": 0.01,
        "max_rated_epochs": 3,
        "max_session_ticks": 10**9,
        "max_session_interventions": 10**6,
        "max_failed_deliveries": 5,
        "temperature": 0.2,
        "model_base_url": "unused",
        "api_key": "unused",
        "envd_url": "http://127.0.0.1:1",
        "provider": "test-provider",
        "model": "test-model",
        "harness_version": ScriptedAgentSession.harness_version,
        "system_prompt_hash": "sp",
        "tool_manifest_hash": "tm",
        "inference_settings_hash": "is",
    }
    defaults.update(overrides)

    class Args:
        pass

    args = Args()
    for key, value in defaults.items():
        setattr(args, key, value)
    return args


def _write_recipe_dump(tmp_path) -> str:
    path = tmp_path / "recipes.json"
    if not path.exists():
        path.write_text(json.dumps(RECIPES), encoding="utf-8")
    return str(path)


def test_end_to_end_session_loop(tmp_path, fake_client_factory):
    client = fake_client_factory(max_epochs=3)
    output = tmp_path / "session.json"

    import scripts.adaptive_contract_benchmark as runner

    record = runner.asyncio.run(run_session(_args(tmp_path, output=output)))

    # One conversation, several epochs through one lease; 1-based indexes.
    assert client.begun == [1, 2, 3]
    assert len(client.finalized) == 3
    assert client.released
    statuses = {o.status for o in client.finalized}
    assert statuses == {"fulfilled"}

    # Rating advanced across rated epochs.
    assert record.final_rating is not None
    assert record.final_rating.mu > 0.0
    assert record.final_rating.rated_epoch_count == 3
    ratings = [e.rating_after.mu for e in record.epochs if e.rating_after is not None]
    assert ratings[0] > 0.0

    # Commitments chain correctly and are unique.
    hashes = [e.spec.commitment_hash for e in record.epochs]
    assert len(set(hashes)) == 3
    assert [e.outcome.commitment_hash for e in record.epochs] == hashes

    # Record persisted atomically at the output path.
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted["result_schema_version"] == "adaptive-result-1"
    assert persisted["participant"]["provider"] == "test-provider"
    assert record.participant.system_prompt_hash != "sp"
    assert record.participant.tool_manifest_hash != "tm"
    assert record.participant.inference_settings_hash != "is"
    assert all(epoch.outcome.model_seconds > 0 for epoch in record.epochs)

    selection = json.loads(
        (tmp_path / "session-epochs" / "epoch-0001.selection.json").read_text(
            encoding="utf-8"
        )
    )
    assert selection["status"] == "committed"
    assert selection["candidate_pool"]
    assert selection["committed_spec"]["epoch_index"] == 1
    active = json.loads((tmp_path / "active-order.json").read_text(encoding="utf-8"))
    assert active["epoch_index"] == 3
    assert active["status"] == "fulfilled"


def test_repetition_filter_cannot_become_order_ceiling(tmp_path, fake_client_factory):
    client = fake_client_factory(max_epochs=5)
    args = _args(
        tmp_path,
        output=tmp_path / "long-session.json",
        max_rated_epochs=5,
    )

    import scripts.adaptive_contract_benchmark as runner

    record = runner.asyncio.run(run_session(args))

    assert client.begun == [1, 2, 3, 4, 5]
    assert len(record.epochs) == 5
    assert "termination_reason=configured_stopping_rule" in record.notes


def test_runner_wall_clock_interrupt_marks_infrastructure(
    tmp_path, fake_client_factory, monkeypatch
):
    """A hung provider is interrupted without becoming a loss."""
    fake_client_factory(max_epochs=2)
    output = tmp_path / "hung.json"

    import scripts.adaptive_contract_benchmark as runner

    args = _args(
        tmp_path,
        run_id="hung-test",
        output=output,
        wall_clock_failsafe_seconds=0.05,
        max_rated_epochs=2,
    )

    original_run_epoch = ScriptedAgentSession.run_epoch

    async def slow_run_epoch(self, prompt):
        import asyncio

        await asyncio.sleep(0.5)
        return await original_run_epoch(self, prompt)

    saved = ScriptedAgentSession.run_epoch
    ScriptedAgentSession.run_epoch = slow_run_epoch
    try:
        record = runner.asyncio.run(run_session(args))
    finally:
        ScriptedAgentSession.run_epoch = saved

    assert record.infrastructure_error_count >= 1
    infra_epochs = [
        e for e in record.epochs if e.outcome.status == "infrastructure_error"
    ]
    assert infra_epochs
    assert all(e.mapped_result == "unrated" for e in infra_epochs)
    assert record.final_rating.rated_epoch_count < len(record.epochs)
