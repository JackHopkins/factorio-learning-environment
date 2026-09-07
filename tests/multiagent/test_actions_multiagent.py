"""Multi-agent action, persistence, and messaging integration tests."""

from fle.commons.models.game_state import GameState


def _entity_signature(entity):
    return entity.name, round(entity.position.x, 3), round(entity.position.y, 3)


def _assert_position(entity, x, y):
    assert abs(entity.position.x - x) <= 0.5
    assert abs(entity.position.y - y) <= 0.5


def test_multiagent_actions_with_messages(multi_instance):
    programs = [
        (
            0,
            """
def place_inserter_at(x, y):
    return place_entity(Prototype.BurnerInserter, Direction.RIGHT, Position(x=x, y=y))
inserter1 = place_inserter_at(-5, -5)
send_message("I've placed a burner inserter at (-5, -5)", recipient=1)
""",
        ),
        (
            1,
            """
def place_furnace_at(x, y):
    return place_entity(Prototype.StoneFurnace, Direction.RIGHT, Position(x=x, y=y))
furnace1 = place_furnace_at(5, 5)
send_message("I've placed a stone furnace at (5, 5)", recipient=0)
""",
        ),
        (
            0,
            """
inserter2 = place_inserter_at(0, -5)
send_message("I've placed another burner inserter at (0, -5)", recipient=1)
""",
        ),
        (
            1,
            """
furnace2 = place_furnace_at(5, -5)
send_message("I've placed another stone furnace at (5, -5)", recipient=0)
""",
        ),
    ]

    for agent_idx, code in programs:
        _, _, response = multi_instance.eval(code, agent_idx=agent_idx)
        assert "error" not in response.lower()
        multi_instance.reset(GameState.from_instance(multi_instance))

    namespace_0, namespace_1 = multi_instance.namespaces
    assert callable(namespace_0.persistent_vars["place_inserter_at"])
    assert "place_furnace_at" not in namespace_0.persistent_vars
    assert callable(namespace_1.persistent_vars["place_furnace_at"])
    assert "place_inserter_at" not in namespace_1.persistent_vars

    placed_entities = [
        namespace_0.persistent_vars["inserter1"],
        namespace_0.persistent_vars["inserter2"],
        namespace_1.persistent_vars["furnace1"],
        namespace_1.persistent_vars["furnace2"],
    ]
    assert [entity.name for entity in placed_entities] == [
        "burner-inserter",
        "burner-inserter",
        "stone-furnace",
        "stone-furnace",
    ]
    for entity, position in zip(placed_entities, [(-5, -5), (0, -5), (5, 5), (5, -5)]):
        _assert_position(entity, *position)

    expected_entities = {_entity_signature(entity) for entity in placed_entities}
    for namespace in (namespace_0, namespace_1):
        visible_entities = namespace.get_entities()
        actual_entities = {
            _entity_signature(entity)
            for entity in visible_entities
            if entity.name in {"burner-inserter", "stone-furnace"}
        }
        assert actual_entities == expected_entities

    agent_0_messages = namespace_0.get_messages()
    agent_1_messages = namespace_1.get_messages()
    assert {
        (message["sender"], str(message["recipient"]), message["message"])
        for message in agent_0_messages
    } == {
        ("1", "0", "I've placed a stone furnace at (5, 5)"),
        ("1", "0", "I've placed another stone furnace at (5, -5)"),
    }
    assert {
        (message["sender"], str(message["recipient"]), message["message"])
        for message in agent_1_messages
    } == {
        ("0", "1", "I've placed a burner inserter at (-5, -5)"),
        ("0", "1", "I've placed another burner inserter at (0, -5)"),
    }
