# send_message

The `send_message` tool allows you to send messages to other agents in the Factorio world. This tool is essential for agent-to-agent communication and coordination.

## Basic Usage

```python
# Send a message to all other agents
send_message("Hello, everyone!")

# Send a message to a specific agent
recipient_id = 2
send_message("I need iron plates", recipient=recipient_id)
```

The function returns `True` if the message was sent successfully.

## Parameters

- `message`: The message text to send (required)
- `recipient`: The player index of the recipient agent (optional, if None, message is sent to all agents)

## Examples

### Broadcasting to All Agents
```python
# Announce a new resource discovery
send_message("I found a large iron ore deposit at position (100, 200)")
```

### Requesting Resources
```python
# Ask another agent for resources
agent_id = 3
send_message("Can you provide 50 iron plates?", recipient=agent_id)
```

### Coordinating Construction
```python
# Coordinate with another agent on construction
agent_id = 2
send_message("I'm building a power plant at (50, 50), please avoid that area", recipient=agent_id)
```

## Common Pitfalls

1. **Invalid Recipient**
   - Sending to a non-existent agent index will not raise an error
   - Always verify agent existence before sending targeted messages

2. **Message Length**
   - Very long messages may be truncated
   - Keep messages concise and to the point

## Best Practices

1. **Structured Messages**
```python
# Use a consistent message format for easier parsing
resource_type = "iron_plate"
quantity = 100
send_message(f"REQUEST:{resource_type}:{quantity}")
```

2. **Response Handling**
```python
# Send a request and wait for a response
request_id = "req_123"
send_message(f"REQUEST:{request_id}:iron_plate:50")

# Later, check for responses
messages = get_messages()
for msg in messages:
    if f"RESPONSE:{request_id}" in msg['message']:
        # Process the response
        process_response(msg)
```

3. **Periodic Status Updates**
```python
# Send periodic status updates to all agents
while True:
    # Get current status
    status = get_current_status()
    
    # Broadcast status
    send_message(f"STATUS:{status}")
    
    # Wait before next update
    sleep(60)
``` 