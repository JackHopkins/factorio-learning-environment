from fle.env.gym_env.observation_formatter import BasicObservationFormatter
from fle.env.gym_env.observation import Observation, GameInfo, AgentMessage
from fle.commons.models.achievements import ProductionFlows
from fle.commons.models.research_state import ResearchState
from fle.commons.models.technology_state import TechnologyState
from fle.agents.models import TaskResponse


def make_minimal_observation(**kwargs):
    # Provide minimal valid values for all required fields
    return Observation(
        raw_text=kwargs.get("raw_text", "Test output"),
        entities=kwargs.get(
            "entities", ["Entity(name=burner-mining-drill, position=(10,5))"]
        ),
        inventory=kwargs.get("inventory", {"iron-ore": 100, "coal": 50}),
        research=kwargs.get(
            "research",
            ResearchState(
                technologies={
                    "automation": TechnologyState(
                        name="automation",
                        researched=True,
                        enabled=True,
                        level=1,
                        research_unit_count=10,
                        research_unit_energy=30.0,
                        prerequisites=["logistics"],
                        ingredients=[{"item": "iron-gear-wheel", "amount": 1}],
                    )
                },
                current_research="automation",
                research_progress=0.5,
                research_queue=["automation"],
                progress={"automation": 0.5},
            ),
        ),
        game_info=kwargs.get("game_info", GameInfo(tick=123, time=2.0, speed=1.0)),
        score=kwargs.get("score", 42.0),
        flows=kwargs.get(
            "flows",
            ProductionFlows(
                input={"coal": 1.5},
                output={"iron-ore": 0.75},
                crafted=[{"type": "iron-gear-wheel", "count": 2}],
                harvested={"iron-ore": 10.0},
                price_list={"iron-ore": 3.0},
                static_items={"iron-ore": 100.0},
            ),
        ),
        task_verification=kwargs.get(
            "task_verification",
            TaskResponse(success=False, meta={"criteria": "Place mining drill"}),
        ),
        messages=kwargs.get(
            "messages",
            [AgentMessage(sender="1", content="Need more iron plates", timestamp=1.0)],
        ),
        serialized_functions=kwargs.get(
            "serialized_functions", [{"name": "dummy_func", "pickled_function": ""}]
        ),
    )


def test_inventory_formatting():
    make_minimal_observation()
    formatter = BasicObservationFormatter()
    formatted = formatter.format_inventory(
        [{"type": "iron-ore", "quantity": 100}, {"type": "coal", "quantity": 50}]
    )
    assert "iron-ore" in formatted and "coal" in formatted
    assert formatted.startswith("### Inventory")


def test_entities_formatting():
    obs = make_minimal_observation()
    formatter = BasicObservationFormatter()
    formatted = formatter.format_entities(obs.entities)
    assert "burner-mining-drill" in formatted or "Entity" in formatted
    assert formatted.startswith("### Entities")


def test_flows_formatting():
    obs = make_minimal_observation()
    formatter = BasicObservationFormatter()
    flows_dict = obs.flows.to_dict()
    # Convert to observation space format
    flows_obs = {
        "input": [{"type": k, "rate": v} for k, v in flows_dict["input"].items()],
        "output": [{"type": k, "rate": v} for k, v in flows_dict["output"].items()],
        "crafted": flows_dict["crafted"],
        "harvested": [
            {"type": k, "amount": v} for k, v in flows_dict["harvested"].items()
        ],
        "price_list": [
            {"type": k, "price": v} for k, v in (flows_dict["price_list"] or {}).items()
        ],
        "static_items": [
            {"type": k, "value": v}
            for k, v in (flows_dict["static_items"] or {}).items()
        ],
    }
    formatted = formatter.format_flows(flows_obs)
    assert "Production Flows" in formatted
    assert "Inputs" in formatted and "Outputs" in formatted


def test_research_formatting():
    make_minimal_observation()
    formatter = BasicObservationFormatter()
    research_dict = {
        "technologies": {
            "automation": {
                "name": "automation",
                "researched": 1,
                "enabled": 1,
                "level": 1,
                "research_unit_count": 10,
                "research_unit_energy": 30.0,
                "prerequisites": ["logistics"],
                "ingredients": [{"item": "iron-gear-wheel", "amount": 1}],
            }
        },
        "current_research": "automation",
        "research_progress": 0.5,
        "research_queue": ["automation"],
        "progress": [{"name": "automation", "value": 0.5}],
    }
    formatted = formatter.format_research(research_dict)
    assert "Research" in formatted
    assert "automation" in formatted


def test_task_formatting():
    formatter = BasicObservationFormatter()
    task = {
        "success": False,
        "meta": [{"key": "criteria", "value": "Place mining drill"}],
    }
    formatted = formatter.format_task(task)
    assert "Task Status" in formatted
    assert "IN PROGRESS" in formatted


def test_messages_formatting():
    formatter = BasicObservationFormatter()
    messages = [
        {"sender": "1", "content": "Need more iron plates", "timestamp": 1.0},
        {"sender": "2", "content": "I'll help with that", "timestamp": 2.0},
    ]
    formatted = formatter.format_messages(messages, last_timestamp=0.0)
    assert "Messages" in formatted
    assert "Agent 1" in formatted and "Agent 2" in formatted


def test_functions_formatting():
    formatter = BasicObservationFormatter()
    # Use an invalid pickled function to test error handling
    functions = [{"name": "dummy_func", "pickled_function": ""}]
    formatted = formatter.format_functions(functions)
    assert "Available Functions" in formatted
    assert "dummy_func" in formatted


def test_raw_text_formatting():
    formatter = BasicObservationFormatter()
    formatted = formatter.format_raw_text("Some output")
    assert "Raw Output" in formatted
    assert "Some output" in formatted


def test_full_format():
    obs = make_minimal_observation()
    formatter = BasicObservationFormatter()
    formatted = formatter.format(obs)
    # Check that all major sections are present
    assert "Inventory" in formatted.raw_str
    assert "Entities" in formatted.raw_str
    assert "Production Flows" in formatted.raw_str
    assert "Research" in formatted.raw_str
    assert "Task Status" in formatted.raw_str or formatted.task_str == ""
    assert "Messages" in formatted.raw_str
    assert "Available Functions" in formatted.raw_str
    assert "Raw Output" in formatted.raw_str
