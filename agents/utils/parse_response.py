from typing import Optional

from agents import Policy, PolicyMeta
from agents.utils.python_parser import PythonParser


def parse_response(response) -> Optional[Policy]:
    if hasattr(response, "choices"):
        choice = response.choices[0]
        input_tokens = response.usage.prompt_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.completion_tokens if hasattr(response, "usage") else 0
        )
    else:
        choice = response.content[0]
        input_tokens = response.usage.input_tokens if hasattr(response, "usage") else 0
        output_tokens = (
            response.usage.output_tokens if hasattr(response, "usage") else 0
        )

    total_tokens = input_tokens + output_tokens
    try:
        code, text_response = PythonParser.extract_code(choice)
    except Exception as e:
        print(f"Failed to extract code from choice: {str(e)}")
        return None

    if not code:
        return None

    policy = Policy(
        code=code,
        meta=PolicyMeta(
            output_tokens=output_tokens,
            input_tokens=input_tokens,
            total_tokens=total_tokens,
            text_response=text_response,
        ),
    )
    return policy
