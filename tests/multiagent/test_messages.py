"""Integration tests for the current A2A namespace messaging API."""


def messages_for(instance, agent_idx):
    return instance.namespaces[agent_idx].get_messages()


def test_collaborative_scenario(multi_instance):
    multi_instance.namespaces[0].send_message(
        "I've gathered 100 iron plates and 50 copper plates.", recipient=1
    )
    multi_instance.namespaces[1].send_message(
        "I need 20 steel plates to start building.", recipient=0
    )
    multi_instance.namespaces[0].send_message(
        "I'll start producing steel plates right away.", recipient=1
    )

    agent_0_messages = messages_for(multi_instance, 0)
    agent_1_messages = messages_for(multi_instance, 1)
    assert any(
        message["sender"] == "1" and "need 20 steel plates" in message["message"]
        for message in agent_0_messages
    )
    assert [message["sender"] for message in agent_1_messages] == ["0", "0"]
    assert "gathered 100 iron plates" in agent_1_messages[0]["message"]
    assert "steel plates" in agent_1_messages[1]["message"]


def test_send_message_to_specific_agent(multi_instance):
    assert multi_instance.namespaces[0].send_message("Hello Agent 1", recipient=1)

    assert messages_for(multi_instance, 0) == []
    received = messages_for(multi_instance, 1)
    assert len(received) == 1
    assert received[0]["sender"] == "0"
    assert received[0]["recipient"] == "1"
    assert received[0]["message"] == "Hello Agent 1"


def test_send_message_to_all_agents(multi_instance):
    assert multi_instance.namespaces[0].send_message("Hello everyone")

    assert messages_for(multi_instance, 0) == []
    received = messages_for(multi_instance, 1)
    assert len(received) == 1
    assert received[0]["message"] == "Hello everyone"


def test_message_collection_in_conversation(multi_instance):
    multi_instance.namespaces[0].send_message("Hello Agent 1", recipient=1)
    received_text = "\n".join(
        message["message"] for message in messages_for(multi_instance, 1)
    )
    assert "Hello Agent 1" in received_text


def test_message_queue_can_be_cleared(multi_instance):
    multi_instance.namespaces[0].send_message("Hello Agent 1", recipient=1)
    assert len(messages_for(multi_instance, 1)) == 1

    multi_instance.namespaces[1].load_messages([])
    assert messages_for(multi_instance, 1) == []


def test_multiple_messages(multi_instance):
    multi_instance.namespaces[0].send_message("Hello Agent 1", recipient=1)
    multi_instance.namespaces[1].send_message("Hello from Agent 1", recipient=0)

    assert messages_for(multi_instance, 0)[0]["message"] == "Hello from Agent 1"
    assert messages_for(multi_instance, 1)[0]["message"] == "Hello Agent 1"
