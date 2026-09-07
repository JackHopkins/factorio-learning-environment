"""Multi-agent action, persistence, and messaging integration tests."""


def test_concurrent_agent_actions_with_messages(multi_instance):
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
        assert "Error" not in response

    namespace_0, namespace_1 = multi_instance.namespaces
    assert callable(namespace_0.persistent_vars["place_inserter_at"])
    assert "place_furnace_at" not in namespace_0.persistent_vars
    assert callable(namespace_1.persistent_vars["place_furnace_at"])
    assert "place_inserter_at" not in namespace_1.persistent_vars

    entities = namespace_0.get_entities()
    assert sum(entity.type == "inserter" for entity in entities) == 2
    assert sum(entity.type == "furnace" for entity in entities) == 2

    agent_0_messages = [message["message"] for message in namespace_0.get_messages()]
    agent_1_messages = [message["message"] for message in namespace_1.get_messages()]
    assert len(agent_0_messages) == 2
    assert len(agent_1_messages) == 2
    assert any("stone furnace at (5, 5)" in message for message in agent_0_messages)
    assert any("stone furnace at (5, -5)" in message for message in agent_0_messages)
    assert any("burner inserter at (-5, -5)" in message for message in agent_1_messages)
    assert any("burner inserter at (0, -5)" in message for message in agent_1_messages)
