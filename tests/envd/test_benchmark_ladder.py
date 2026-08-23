import pytest

from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    build_capability_ladder,
    render_ladder_markdown,
)

pytestmark = pytest.mark.no_factorio


def _run(
    run_id: str,
    model: str,
    provider: str,
    attempts: list[tuple[str, int, bool, float]],
) -> BenchmarkRun:
    from datetime import datetime, timedelta, timezone

    started = datetime(2026, 8, 22, tzinfo=timezone.utc)
    return BenchmarkRun(
        run_id=run_id,
        model=ModelIdentity(name=model, provider=provider),
        started_at=started,
        completed_at=started + timedelta(minutes=10),
        repository_commit="0" * 40,
        attempts=[
            BenchmarkAttempt(
                task_id=task_id,
                task_fingerprint="fingerprint",
                attempt=index,
                seed=0,
                success=success,
                scalar_reward=reward,
                interventions=3,
                elapsed_seconds=1.0,
            )
            for task_id, index, success, reward in attempts
        ],
    )


def test_elo_orders_models_by_shared_task_performance():
    strong = _run(
        "r1",
        "strong-model",
        "openrouter",
        [
            ("task-a", 0, True, 1.0),
            ("task-b", 0, True, 0.9),
            ("task-c", 0, False, 0.2),
        ],
    )
    weak = _run(
        "r2",
        "weak-model",
        "openrouter",
        [
            ("task-a", 0, False, 0.1),
            ("task-b", 0, False, 0.0),
            ("task-c", 0, True, 1.0),
        ],
    )
    ladder = build_capability_ladder([strong, weak])

    rows = {row["model_key"]: row for row in ladder["ladder"]}
    assert ladder["game_count"] == 3
    assert (
        rows["openrouter/strong-model"]["elo"]
        > rows["openrouter/weak-model"]["elo"]
    )
    assert rows["openrouter/strong-model"]["success_rate"] == pytest.approx(
        2 / 3, abs=1e-3
    )
    assert rows["openrouter/weak-model"]["tasks_covered"] == 3


def test_equal_rewards_draw_and_unshared_tasks_do_not_pair():
    first = _run("r1", "alpha", "zen", [("task-x", 0, True, 0.8)])
    second = _run("r2", "beta", "zen", [("task-x", 0, True, 0.8)])
    third = _run("r3", "gamma", "zen", [("task-y", 0, True, 1.0)])
    ladder = build_capability_ladder([first, second, third])

    # alpha and beta draw on task-x; gamma shares nothing so no games.
    assert ladder["game_count"] == 1
    ratings = {row["model_key"]: row["elo"] for row in ladder["ladder"]}
    assert ratings["zen/alpha"] == pytest.approx(ratings["zen/beta"])
    assert ratings["zen/gamma"] == 1200.0


def test_best_attempt_per_task_wins_across_multiple_attempts():
    run = _run(
        "r1",
        "multi",
        "local",
        [
            ("task-a", 0, False, 0.2),
            ("task-a", 1, True, 1.0),
            ("task-a", 2, False, 0.5),
        ],
    )
    ladder = build_capability_ladder([run])
    row = ladder["ladder"][0]
    assert row["attempt_count"] == 3
    assert row["mean_reward"] == pytest.approx((0.2 + 1.0 + 0.5) / 3, abs=1e-3)
    assert row["success_rate"] == pytest.approx(1 / 3, abs=1e-3)


def test_rewards_are_capped_to_unit_interval():
    run = _run("r1", "capped", "local", [("task-z", 0, True, 4.2)])
    ladder = build_capability_ladder([run])
    assert ladder["ladder"][0]["mean_reward"] == pytest.approx(1.0)


def test_markdown_renders_sorted_rows():
    strong = _run("r1", "strong", "p", [("t", 0, True, 1.0)])
    weak = _run("r2", "weak", "p", [("t", 0, False, 0.1)])
    markdown = render_ladder_markdown(build_capability_ladder([strong, weak]))
    lines = [line for line in markdown.splitlines() if line.startswith("| ")]
    # Header row + two model rows; the separator starts with "|---".
    assert len(lines) == 3
    assert "strong" in lines[1]
