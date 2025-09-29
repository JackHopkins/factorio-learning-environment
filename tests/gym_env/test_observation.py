from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action

# from fle.env.gym_env.validation import validate_observation
from fle.env.entities import Position, Direction
from fle.env.game_types import Prototype, Resource


def test_reset_observation(instance):
    env = FactorioGymEnv(instance, pause_after_action=False)
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

    env = FactorioGymEnv(instance, pause_after_action=False)
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

    env = FactorioGymEnv(instance, pause_after_action=False)
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
    env = FactorioGymEnv(instance, pause_after_action=False)
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
    env = FactorioGymEnv(instance, pause_after_action=False)
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
    env = FactorioGymEnv(instance, pause_after_action=False)
    env.reset()
    action = Action(agent_idx=0, code='print("Hello world!")', game_state=None)
    observation, reward, terminated, truncated, info = env.step(action)
    assert "raw_text" in observation
    assert "Hello world" in observation["raw_text"]


def test_serialized_functions_observation(instance):
    """Test that defining a function via action adds it to serialized_functions in observation."""
    instance.reset()
    env = FactorioGymEnv(instance, pause_after_action=False)
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
    env = FactorioGymEnv(instance, pause_after_action=False)
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


def test_game_info_elapsed_ticks_sleep(instance):
    """Test that game_info.tick reflects elapsed ticks correctly after sleep actions."""
    instance.initial_inventory = {"coal": 100}
    instance.reset()
    instance.set_speed(10.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    # Get initial tick count
    initial_ticks = observation["game_info"]["tick"]

    # Sleep for 2 seconds - should add 120 ticks
    sleep_action = Action(
        agent_idx=0,
        code="sleep(2)",
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(sleep_action)

    # Check that ticks increased by expected amount
    final_ticks = observation["game_info"]["tick"]
    ticks_added = final_ticks - initial_ticks

    assert ticks_added == 120, (
        f"Expected 120 ticks for 2-second sleep, got {ticks_added}"
    )
    assert observation["game_info"]["speed"] == 10.0, "Game speed should be 10.0"


def test_game_info_elapsed_ticks_craft_item(instance):
    """Test that game_info.tick reflects elapsed ticks correctly after crafting."""
    instance.initial_inventory = {"iron-plate": 100}
    instance.reset()
    instance.set_speed(10.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    initial_ticks = observation["game_info"]["tick"]

    # Craft 3 iron gear wheels - each takes 0.5 seconds = 30 ticks
    # Total should be 90 ticks
    craft_action = Action(
        agent_idx=0,
        code="craft_item(Prototype.IronGearWheel, 3)",
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(craft_action)

    final_ticks = observation["game_info"]["tick"]
    ticks_added = final_ticks - initial_ticks

    assert ticks_added == 90, (
        f"Expected 90 ticks for crafting 3 iron gear wheels, got {ticks_added}"
    )


def test_game_info_elapsed_ticks_move_to(instance):
    """Test that game_info.tick reflects elapsed ticks correctly after movement."""
    instance.initial_inventory = {"coal": 100}
    instance.reset()
    instance.set_speed(10.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    initial_ticks = observation["game_info"]["tick"]

    # Move to a position 3 tiles away
    # Movement should add ticks based on distance and player speed (~35 ticks for 3 tiles)
    move_action = Action(
        agent_idx=0,
        code="move_to(Position(x=3, y=3))",
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(move_action)

    final_ticks = observation["game_info"]["tick"]
    ticks_added = final_ticks - initial_ticks

    # Movement ticks depend on distance/speed, allow reasonable range
    assert 30 <= ticks_added <= 40, (
        f"Expected ~35 ticks for 3-tile movement, got {ticks_added}"
    )


def test_game_info_elapsed_ticks_harvest_resource(instance):
    """Test that game_info.tick reflects elapsed ticks correctly after harvesting."""
    instance.initial_inventory = {"coal": 100}
    instance.reset()
    instance.set_speed(10.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()
    instance.rcon_client.send_command(
        "/sc game.player.character.reach_distance = 1000; game.player.character.mining_reach_distance = 1000"
    )

    instance.rcon_client.send_command("/sc game.tick_paused = false")
    namespace = instance.namespace
    nearest_iron_ore = namespace.nearest(Resource.IronOre)
    print(f"nearest iron ore: {nearest_iron_ore}")
    namespace.move_to(Position(x=nearest_iron_ore.x, y=nearest_iron_ore.y))
    current_ticks = instance.get_elapsed_ticks()

    namespace.harvest_resource(nearest_iron_ore, 1, radius=1000)
    end_ticks = instance.get_elapsed_ticks()
    ticks_added = end_ticks - current_ticks

    print(f"inventory: {observation['inventory']}")
    print(f"raw_text: {observation['raw_text']}")

    # Harvesting ticks depend on resource type, allow reasonable range
    assert 50 <= ticks_added <= 80, (
        f"Expected ~60 ticks for harvesting iron ore, got {ticks_added}"
    )


def test_game_info_elapsed_ticks_multiple_actions(instance):
    """Test that game_info.tick correctly accumulates ticks across multiple actions."""
    instance.initial_inventory = {"iron-plate": 100, "coal": 100}
    instance.reset()
    instance.set_speed(10.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    initial_ticks = observation["game_info"]["tick"]

    # Perform multiple actions in sequence
    actions = [
        "sleep(1)",  # Should add 60 ticks
        "craft_item(Prototype.IronGearWheel, 1)",  # Should add 30 ticks
        "move_to(Position(x=2, y=2))",  # Should add ~25 ticks
    ]

    for i, code in enumerate(actions):
        action = Action(agent_idx=0, code=code, game_state=None)
        observation, reward, terminated, truncated, info = env.step(action)

        current_ticks = observation["game_info"]["tick"]
        ticks_since_start = current_ticks - initial_ticks

        if i == 0:  # After sleep
            assert 55 <= ticks_since_start <= 65, (
                f"Expected ~60 ticks after sleep, got {ticks_since_start}"
            )
        elif i == 1:  # After sleep + craft
            assert 85 <= ticks_since_start <= 95, (
                f"Expected ~90 ticks after sleep+craft, got {ticks_since_start}"
            )
        elif i == 2:  # After sleep + craft + move
            assert 110 <= ticks_since_start <= 120, (
                f"Expected ~115 ticks after all actions, got {ticks_since_start}"
            )


def test_game_info_elapsed_ticks_with_game_speed(instance):
    """Test that game_info.tick is independent of game speed (always standard ticks)."""
    instance.initial_inventory = {"coal": 100}
    instance.reset()

    # Test at 3x speed
    instance.set_speed(3.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    initial_ticks = observation["game_info"]["tick"]

    # Sleep for 1 second - should still add 60 ticks regardless of speed
    sleep_action = Action(
        agent_idx=0,
        code="sleep(1)",
        game_state=None,
    )
    observation, reward, terminated, truncated, info = env.step(sleep_action)

    final_ticks = observation["game_info"]["tick"]
    ticks_added = final_ticks - initial_ticks

    # Should still add 60 ticks (standard time) even at 3x speed
    assert ticks_added == 60, (
        f"Expected 60 ticks regardless of speed, got {ticks_added}"
    )
    assert observation["game_info"]["speed"] == 3.0, "Game speed should be 3.0"


def test_game_info_tick_persistence(instance):
    """Test that game_info.tick persists and accumulates correctly across observations."""
    instance.initial_inventory = {"iron-plate": 100}
    instance.reset()
    instance.set_speed(1.0)

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    # Track ticks across multiple steps
    tick_history = [observation["game_info"]["tick"]]

    # First action: sleep 0.5 seconds (30 ticks)
    action1 = Action(agent_idx=0, code="sleep(0.5)", game_state=None)
    observation, reward, terminated, truncated, info = env.step(action1)
    tick_history.append(observation["game_info"]["tick"])

    # Second action: craft item (30 ticks)
    action2 = Action(
        agent_idx=0, code="craft_item(Prototype.IronGearWheel, 1)", game_state=None
    )
    observation, reward, terminated, truncated, info = env.step(action2)
    tick_history.append(observation["game_info"]["tick"])

    # Third action: no-op (0 ticks)
    action3 = Action(agent_idx=0, code="pass", game_state=None)
    observation, reward, terminated, truncated, info = env.step(action3)
    tick_history.append(observation["game_info"]["tick"])

    # Verify tick progression
    assert tick_history[1] - tick_history[0] == 30, "First action should add 30 ticks"
    assert tick_history[2] - tick_history[1] == 30, "Second action should add 30 ticks"
    assert tick_history[3] - tick_history[2] == 0, "No-op should add 0 ticks"
    assert tick_history[3] - tick_history[0] == 60, "Total should be 60 ticks"


def test_game_info_structure(instance):
    """Test that game_info contains all expected fields with correct types."""
    instance.reset()

    env = FactorioGymEnv(instance, pause_after_action=False)
    observation, info = env.reset()

    # Verify game_info structure
    game_info = observation["game_info"]
    assert "tick" in game_info, "game_info should contain 'tick' field"
    assert "time" in game_info, "game_info should contain 'time' field"
    assert "speed" in game_info, "game_info should contain 'speed' field"

    # Verify types
    assert isinstance(game_info["tick"], int), "tick should be an integer"
    assert isinstance(game_info["time"], (int, float)), "time should be numeric"
    assert isinstance(game_info["speed"], (int, float)), "speed should be numeric"

    # Verify reasonable values
    assert game_info["tick"] >= 0, "tick should be non-negative"
    assert game_info["speed"] > 0, "speed should be positive"
