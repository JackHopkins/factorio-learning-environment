from typing import List, Dict, Any


def merge_contiguous_messages(messages):
    if not messages:
        return messages

    merged_messages = [messages[0]]

    for message in messages[1:]:
        if message["role"] == merged_messages[-1]["role"]:
            # Only merge if both are simple text content
            if isinstance(merged_messages[-1]["content"], str) and isinstance(
                message["content"], str
            ):
                merged_messages[-1]["content"] += "\n\n" + message["content"]
            else:
                # If either has complex content (like images), don't merge
                merged_messages.append(message)
        else:
            merged_messages.append(message)

    return merged_messages


def remove_whitespace_blocks(messages):
    return [
        message
        for message in messages
        if (isinstance(message["content"], str) and message["content"].strip())
        or (isinstance(message["content"], list) and len(message["content"]) > 0)
    ]


def has_image_content(messages: List[Dict[str, Any]]) -> bool:
    """Check if any message contains image content."""
    for message in messages:
        content = message.get("content", [])
        # Handle content as list (multimodal) or string (text only)
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and (
                    item.get("type") == "image" or item.get("type") == "image_url"
                ):
                    return True
        # OpenAI format may use content_parts
        if "content_parts" in message:
            for part in message["content_parts"]:
                if isinstance(part, dict) and (
                    part.get("type") == "image" or part.get("type") == "image_url"
                ):
                    return True
    return False


def format_messages_for_anthropic(
    messages: List[Dict[str, Any]], system_message: str
) -> List[Dict[str, Any]]:
    """Format messages for Anthropic API with image support."""
    formatted_messages = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        # Skip system message as it's handled separately in Anthropic API
        if role == "system":
            continue

        # Convert to Anthropic format
        formatted_message = {"role": role}

        # Handle multimodal content
        if isinstance(content, list):
            formatted_content = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        formatted_content.append(
                            {"type": "text", "text": item.get("text", "")}
                        )
                    elif item.get("type") == "image" and "source" in item:
                        formatted_content.append(
                            {"type": "image", "source": item["source"]}
                        )
                    elif item.get("type") == "image_url":
                        # Convert OpenAI format to Anthropic format
                        image_url = item.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image/"):
                            # Extract the base64 data and media type from data URL
                            media_type = image_url.split(";")[0].split(":")[1]
                            base64_data = image_url.split(",")[1]
                            formatted_content.append(
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": base64_data,
                                    },
                                }
                            )
                        else:
                            # For regular URLs
                            formatted_content.append(
                                {
                                    "type": "image",
                                    "source": {"type": "url", "url": image_url},
                                }
                            )
        else:
            # Handle simple text content
            formatted_content = [{"type": "text", "text": content}]

        formatted_message["content"] = formatted_content
        formatted_messages.append(formatted_message)

    return formatted_messages


def format_messages_for_openai(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format messages for OpenAI API with image support."""
    formatted_messages = []

    for message in messages:
        role = message["role"]
        content = message["content"]

        # Convert to OpenAI format
        formatted_message = {"role": role}

        # Handle multimodal content
        if isinstance(content, list):
            formatted_content = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        formatted_content.append(
                            {"type": "text", "text": item.get("text", "")}
                        )
                    elif item.get("type") == "image" and "source" in item:
                        # Convert Anthropic format to OpenAI format
                        source = item["source"]
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/jpeg")
                            base64_data = source.get("data", "")
                            formatted_content.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{media_type};base64,{base64_data}"
                                    },
                                }
                            )
                        elif source.get("type") == "url":
                            formatted_content.append(
                                {
                                    "type": "image_url",
                                    "image_url": {"url": source.get("url", "")},
                                }
                            )

            formatted_message["content"] = formatted_content
        else:
            # Handle simple text content
            formatted_message["content"] = content

        formatted_messages.append(formatted_message)

    return formatted_messages
