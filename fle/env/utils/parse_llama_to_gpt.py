import json


def parse_and_format(data):
    # Extract needed data
    messages = data.get("input", [])

    # Include output in the messages list if it exists
    if "output" in data:
        messages.append(data["output"])

    # Transform the messages into the desired output format
    output_messages = {
        "messages": [
            {
                "role": msg["role"],
                "content": msg["message"].replace("Recent History: \n", ""),
            }
            for msg in messages
        ]
    }

    # Convert back to JSON string format for each message set
    return json.dumps(output_messages)


if __name__ == "__main__":
    # Read the JSON string

    # Call the function to parse and format the JSONL string from /Users/jackhopkins/PycharmProjects/PaperclipMaximiser/src/llama_events.jsonl

    # Get lines from the file
    file = open("//llama_events.jsonl")
    out_file = open("//gpt_events.jsonl", "w")

    # json_obj = json.loads(file.read())
    lines = file.readlines()

    # Parse each line
    for line in lines:
        # Parse the JSON string into a dictionary
        data = json.loads(line)
        output_json = parse_and_format(data)

        print(output_json)

        # Append to the jsonl file
        out_file.write(output_json + "\n")

    # Close the file
    file.close()
