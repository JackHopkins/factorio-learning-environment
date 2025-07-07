import json
import re
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class Node:
    number: str
    content: str
    children: List["Node"]


def parse_hierarchy(text: str) -> Node:
    """Parse the hierarchical text into a tree structure."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    root = Node("0", "root", [])
    current_path = [root]

    for line in lines:
        # Extract the number and content
        match = re.match(r"^(\d+(\.\d+)*)\.\s+(.+)$", line)
        if not match:
            continue

        number, _, content = match.groups()
        depth = len(number.split("."))

        # Create new node
        new_node = Node(number, content, [])

        # Adjust current path
        while len(current_path) > depth:
            current_path.pop()
        if len(current_path) < depth:
            current_path.append(current_path[-1])

        # Add node to parent
        current_path[-1].children.append(new_node)
        current_path[-1] = new_node

    return root


def generate_training_examples(root: Node) -> List[Tuple[str, str]]:
    """Generate training examples from the tree structure."""
    examples = []

    def process_node(node: Node, history: List[str]):
        if not node.children:
            return

        # Generate examples for direct children prediction
        history_text = (
            "\n".join(history + [f"{node.number}. {node.content}"])
            .replace("0. root", "")
            .strip()
        )

        # If node has children, create example for predicting all children
        if node.children:
            history_text += "\n    <>".replace("0. root", "").strip()
            output = "\n".join(
                [f"{child.number}. {child.content}" for child in node.children]
            )
            examples.append((history_text, output))

        # For each child with siblings, create examples for predicting next sibling
        for i, child in enumerate(node.children[:-1]):
            sibling_history = (
                history
                + [f"{node.number}. {node.content}"]
                + [
                    f"   {node.children[j].number}. {node.children[j].content}"
                    for j in range(i + 1)
                ]
            )
            sibling_history_text = (
                "\n".join(sibling_history + ["   <>"]).replace("0. root", "").strip()
            )
            output = f"{node.children[i + 1].number}. {node.children[i + 1].content}"
            examples.append((sibling_history_text, output))

        # For the last child, predict </> token
        if node.children:
            last_child = node.children[-1]
            leaf_history = history + [
                f"{node.number}. {node.content}",
                f"   {last_child.number}. {last_child.content}",
                "   <>",
            ]
            input_str = "\n".join(leaf_history).replace("0. root", "").strip()
            examples.append((input_str, "</>"))

        # Recursively process children
        for child in node.children:
            process_node(child, history + [f"{node.number}. {node.content}"])

    process_node(root, [])
    return examples


def process_file(content: str) -> List[Tuple[str, str]]:
    """Process the file content and return training examples."""
    root = parse_hierarchy(content)
    return generate_training_examples(root)


def main():
    output_file = "factorio_relationships.jsonl"

    processed_dir = Path("./factorio_guides/processed")
    with open(output_file, "a") as fo:
        for file in processed_dir.glob("*.xml"):
            # parser.save_relationships_jsonl(str(file), output_file)
            with open(file, "r") as f:
                content = f.read()
            try:
                content = "1. " + content.split("\n1. ")[1]
                pass
            except:
                pass

            content = content.replace("**", "")

            examples = process_file(content)

            # Save to a format suitable for OpenAI finetuning
            for input_text, output_text in examples:
                fo.write(
                    json.dumps(
                        {
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a helpful assistant that decides on the most appropriate Factorio game objective",
                                },
                                {"role": "user", "content": input_text},
                                {"role": "assistant", "content": output_text},
                            ]
                        }
                    )
                    + "\n"
                )
                print({"prompt": input_text, "completion": output_text})


if __name__ == "__main__":
    main()
