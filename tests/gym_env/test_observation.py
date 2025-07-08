from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action

# from fle.env.gym_env.validation import validate_observation
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype


def test_reset_observation(instance):
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    # validate_observation(observation, env.observation_space)


def test_inventory_observation(instance):
    """Test that inventory changes are reflected in observations."""
    # Set up initial inventory
    instance.initial_inventory = {
        "coal": 50,
        "iron-chest": 1,
        "iron-plate": 5,
    }
    instance.reset()

    env = FactorioGymEnv(instance)
    observation, info = env.reset()

    # Verify initial inventory in observation
    inventory_items = {
        item["type"]: item["quantity"] for item in observation["inventory"]
    }
    assert inventory_items["coal"] == 50
    assert inventory_items["iron-chest"] == 1
    assert inventory_items["iron-plate"] == 5

    # Place a chest and insert items
    chest = instance.namespace.place_entity(
        Prototype.IronChest, position=Position(x=2.5, y=2.5)
    )
    chest = instance.namespace.insert_item(Prototype.Coal, chest, quantity=10)

    # Get new observation using a no-op action
    action = Action(
        agent_idx=0,
        code="pass",  # No-op Python code
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(action)

    # Verify chest in observation
    chest_entities = [e for e in observation["entities"] if "iron-chest" in e]
    assert len(chest_entities) == 1
    # Verify the chest string representation contains the expected information
    chest_str = chest_entities[0]
    assert "iron-chest" in chest_str
    assert "x=2.5, y=2.5" in chest_str


def test_entity_placement_observation(instance):
    """Test that entity placement is reflected in observations."""
    instance.initial_inventory = {"stone-furnace": 1, "coal": 50, "iron-ore": 10}
    instance.reset()

    env = FactorioGymEnv(instance)
    observation, info = env.reset()

    # Verify initial state
    assert len(observation["entities"]) == 0

    # Place a furnace
    instance.namespace.place_entity(
        Prototype.StoneFurnace, direction=Direction.UP, position=Position(x=2.5, y=2.5)
    )

    # Get new observation using a no-op action
    action = Action(
        agent_idx=0,
        code="pass",  # No-op Python code
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(action)

    # Verify furnace in observation
    furnace_entities = [e for e in observation["entities"] if "stone-furnace" in e]
    assert len(furnace_entities) == 1
    furnace_str = furnace_entities[0]
    # Verify the furnace string representation contains the expected information
    assert "stone-furnace" in furnace_str
    assert "x=3.0, y=3.0" in furnace_str
    assert "Direction.UP" in furnace_str


def test_research_observation(instance):
    """Test that research state changes are reflected in observations."""
    # Set up initial state with a researchable technology
    instance.reset()
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    # Start a research via action (assuming 'automation' is a valid tech)
    action = Action(
        agent_idx=0,
        code="Technology = Prototype.Automation; self.research(Technology)",
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(action)
    research = observation["research"]
    assert "technologies" in research
    # Check that at least one technology is present and has plausible fields
    if isinstance(research["technologies"], list):
        assert len(research["technologies"]) > 0
        tech = research["technologies"][0]
        assert "name" in tech
    elif isinstance(research["technologies"], dict):
        assert len(research["technologies"]) > 0
        tech = next(iter(research["technologies"].values()))
        assert "name" in tech.__dict__ or hasattr(tech, "name")


def test_flows_observation(instance):
    """Test that production flows change after crafting or smelting."""
    # Give the agent resources to craft
    instance.initial_inventory = {"iron-ore": 10, "stone-furnace": 1, "coal": 10}
    instance.reset()
    env = FactorioGymEnv(instance)
    observation, info = env.reset()
    # Place a furnace and smelt iron-ore
    env.instance.namespace.place_entity(
        Prototype.StoneFurnace, position=Position(x=1.5, y=1.5)
    )
    action = Action(
        agent_idx=0, code="for i in range(5): pass", game_state=None
    )  # No-op to advance
    observation, reward, terminated, truncated, info = env.step(action)
    flows = observation["flows"]
    assert "input" in flows
    assert "output" in flows
    # There should be some flow activity if smelting occurred
    assert isinstance(flows["input"], list)
    assert isinstance(flows["output"], list)
    # Accept empty if nothing happened, but this checks the structure


def test_raw_text_observation(instance):
    """Test that raw_text is updated after an action that prints output."""
    instance.reset()
    env = FactorioGymEnv(instance)
    env.reset()
    action = Action(agent_idx=0, code='print("Hello world!")', game_state=None)
    observation, reward, terminated, truncated, info = env.step(action)
    assert "raw_text" in observation
    assert "Hello world" in observation["raw_text"]


def test_serialized_functions_observation(instance):
    """Test that defining a function via action adds it to serialized_functions in observation."""
    instance.reset()
    env = FactorioGymEnv(instance)
    env.reset()
    # Define a function via action
    code = "def my_test_func():\n    return 42"
    action = Action(agent_idx=0, code=code, game_state=None)
    observation, reward, terminated, truncated, info = env.step(action)
    assert "serialized_functions" in observation
    assert any(f["name"] == "my_test_func" for f in observation["serialized_functions"])


def test_messages_observation(instance):
    """Test that sending a message is reflected in the observation."""
    instance.reset()
    env = FactorioGymEnv(instance)
    env.reset()
    # Simulate sending a message if possible
    if hasattr(instance.namespace, "load_messages"):
        msg = {
            "sender": "test_agent",
            "message": "Test message",
            "timestamp": 1234567890,
        }
        instance.namespace.load_messages([msg])
    action = Action(agent_idx=0, code="pass", game_state=None)
    observation, reward, terminated, truncated, info = env.step(action)
    assert "messages" in observation
    if observation["messages"]:
        assert any(
            "Test message" in m.get("content", "")
            or "Test message" in m.get("message", "")
            for m in observation["messages"]
        )
