import re
from typing import Optional, Tuple
import ast


def get_default_system_prompt(prompt_object):
        # Combine all parts into final prompt
        return (
            f"```types\n{prompt_object['type_defs']}\n{prompt_object['entity_defs']}\n```\n"
            f"```methods\n{prompt_object['schema']}\n```"
            f"{prompt_object['manual_defs']}\n{prompt_object['examples']}\n"
        )

def get_rag_system_prompt(prompt_object):
        # Combine all parts into final prompt
        return (
            f"```types\n{prompt_object['type_defs']}\n{prompt_object['entity_defs']}\n```\n"
            f"```methods\n{prompt_object['schema']}\n```"
            f"{prompt_object['manual_defs']}\n"
            f"Information gathering tools available to you\n"
            f"{prompt_object['rag_manual_defs']}\n"
        )