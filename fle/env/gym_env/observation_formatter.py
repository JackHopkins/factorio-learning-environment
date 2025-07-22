from dataclasses import dataclass
import pickle
import re

from fle.env.gym_env.observation import Observation
from typing import Any, Dict, List, Optional


@dataclass
class FormattedObservation:
    """Container for formatted observation strings"""

    inventory_str: str
    """Formatted string showing current inventory contents.
    Example:
    ### Inventory
    - iron-ore: 100
    - coal: 50
    - transport-belt: 10
    Items are sorted by quantity in descending order."""

    entities_str: str
    """Formatted string showing entities on the map grouped by type.
    Example:
    ### Entities
    - burner-mining-drill: 2
    - transport-belt: 5
    - inserter: 3
    Entities are grouped and counted by their type."""

    flows_str: str
    """Formatted string showing current production flow rates.
    Example:
    ### Production Flows
    #### Inputs
    - coal: 1.50/s
    #### Outputs
    - iron-ore: 0.75/s
    Shows both input consumption and output production rates per second."""

    task_str: str
    """Formatted string showing task verification status and criteria.
    Example:
    ### Task Status
    ⏳ IN PROGRESS

    **Message:** Need more iron plates

    **Criteria:**
    - ✅ Place mining drill
    - ❌ Produce 100 iron plates
    Empty string if no task is being tracked."""

    messages_str: str
    """Formatted string showing messages received from other agents.
    Example:
    ### Messages
    - **[Agent 1]**: Need more iron plates
    - **[Agent 2]**: I'll help with that
    Empty string if no messages were received."""

    functions_str: str
    """Formatted string showing available functions with their signatures and docstrings.
    Example:
    ### Available Functions
    ```python
    def find_idle_furnaces(entities: List[Entity]) -> List[Entity]
      \"\"\"Find all furnaces that are not currently working.\"\"\"
    ```
    Shows function names, parameter types, return types, and docstrings."""

    raw_text_str: str
    """Formatted string showing the raw text output from the last action.
    Example:
    ### Raw Output
    ```
    Successfully placed mining drill at position (10, 5)
    Current iron ore production: 0.75/s
    ```
    Shows the direct output from the executed code."""

    raw_str: str
    """Complete formatted observation combining all components.
    Example:
    ### Inventory
    - iron-ore: 100
    - coal: 50

    ### Entities
    - burner-mining-drill: 2
    - transport-belt: 5

    ### Production Flows
    #### Inputs
    - coal: 1.50/s
    #### Outputs
    - iron-ore: 0.75/s

    ### Available Functions
    ```python
    def find_idle_furnaces(entities: List[Entity]) -> List[Entity]
      \"\"\"Find all furnaces that are not currently working.\"\"\"
    ```

    ### Task Status
    ⏳ IN PROGRESS

    **Message:** Need more iron plates

    **Criteria:**
    - ✅ Place mining drill
    - ❌ Produce 100 iron plates

    ### Messages
    - **[Agent 1]**: Need more iron plates
    - **[Agent 2]**: I'll help with that

    ### Raw Output
    ```
    Successfully placed mining drill at position (10, 5)
    Current iron ore production: 0.75/s
    ```"""


class BasicObservationFormatter:
    """Formats gym environment observations into helpful strings"""

    def __init__(
        self,
        include_inventory: bool = True,
        include_entities: bool = True,
        include_flows: bool = True,
        include_task: bool = True,
        include_messages: bool = True,
        include_functions: bool = True,
        include_state_changes: bool = True,
        include_raw_output: bool = True,
        include_research: bool = True,
    ):
        """Initialize the formatter with flags for which fields to include"""
        self.include_inventory = include_inventory
        self.include_entities = include_entities
        self.include_flows = include_flows
        self.include_task = include_task
        self.include_messages = include_messages
        self.include_functions = include_functions
        self.include_state_changes = include_state_changes
        self.include_raw_output = include_raw_output
        self.include_research = include_research

    @staticmethod
    def format_inventory(inventory: List[Dict[str, Any]]) -> str:
        """Format inventory information"""
        if not inventory:
            return "### Inventory\nEmpty"

        # Convert list of dicts to dict for easier sorting
        inventory_dict = {
            item["type"]: item["quantity"] for item in inventory if item["quantity"] > 0
        }

        # Sort items by quantity for consistent output
        sorted_items = sorted(inventory_dict.items(), key=lambda x: x[1], reverse=True)

        # Format each item
        item_strs = []
        for item_type, quantity in sorted_items:
            item_strs.append(f"- {item_type}: {quantity}")

        return "### Inventory\n" + "\n".join(item_strs)

    @staticmethod
    def format_entities(entities: List[str]) -> str:
        """Format entity information"""
        if not entities:
            return "### Entities\nNone found"

        def clean_entity_string(entity_str: str) -> str:
            """Clean and format an entity string for better readability"""
            # Remove class references and unnecessary information
            entity_str = entity_str.replace("class 'env.src.entities.", "")
            entity_str = entity_str.replace("'>", "")

            # Split into key-value pairs, being careful with nested structures
            parts = []
            current_part = []
            bracket_level = 0
            quote_level = 0

            for char in entity_str:
                if char == "[":
                    bracket_level += 1
                elif char == "]":
                    bracket_level -= 1
                elif char == "'":
                    quote_level = 1 - quote_level
                elif char == "(":
                    bracket_level += 1
                elif char == ")":
                    bracket_level -= 1

                if char == " " and bracket_level == 0 and quote_level == 0:
                    if current_part:
                        parts.append("".join(current_part))
                        current_part = []
                else:
                    current_part.append(char)

            if current_part:
                parts.append("".join(current_part))

            # Process each part
            formatted_parts = []
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Clean up the value
                    if "Position" in value:
                        # Extract x and y coordinates
                        x_match = re.search(r"x=([\d.]+)", value)
                        y_match = re.search(r"y=([\d.]+)", value)
                        if x_match and y_match:
                            x = float(x_match.group(1))
                            y = float(y_match.group(1))
                            value = f"({x:.1f}, {y:.1f})"
                    elif "Dimensions" in value:
                        # Extract width and height
                        w_match = re.search(r"width=([\d.]+)", value)
                        h_match = re.search(r"height=([\d.]+)", value)
                        if w_match and h_match:
                            w = float(w_match.group(1))
                            h = float(h_match.group(1))
                            value = f"({w:.1f}, {h:.1f})"
                    elif "TileDimensions" in value:
                        # Extract tile width and height
                        w_match = re.search(r"tile_width=([\d.]+)", value)
                        h_match = re.search(r"tile_height=([\d.]+)", value)
                        if w_match and h_match:
                            w = float(w_match.group(1))
                            h = float(h_match.group(1))
                            value = f"({w:.1f}, {h:.1f})"
                    elif "Prototype" in value:
                        # Convert "<Prototype.Boiler: ...>" to "Prototype.Boiler"
                        proto_match = re.search(r"<Prototype\.([^:>]+)[:>]?", value)
                        if proto_match:
                            value = f"Prototype.{proto_match.group(1)}"
                        else:
                            # Fallback: use the part after 'Prototype.' if present
                            alt_match = re.search(r"Prototype\.([A-Za-z0-9_-]+)", value)
                            if alt_match:
                                value = f"Prototype.{alt_match.group(1)}"

                    # Format numbers consistently
                    if isinstance(value, str):
                        # Try to convert to float if it's a number
                        try:
                            num = float(value)
                            value = f"{num:.1f}"
                        except ValueError:
                            pass

                    # Remove any double commas
                    value = re.sub(r",\s*,", ",", value)

                    formatted_parts.append(f"{key}={value}")
                else:
                    formatted_parts.append(part)

            return ", ".join(formatted_parts)

        # Group entities by type
        entity_groups = {}
        name_pattern = re.compile(r"\bname\s*=\s*'?([A-Za-z0-9_-]+)'?")
        group_pattern = re.compile(r"^\s*([A-Za-z]+Group)\(")

        for entity_str in entities:
            # Extract entity type using regex (handles both quoted and unquoted values)
            type_match = None
            # Try to get name first
            n = name_pattern.search(entity_str)
            if n:
                type_match = n.group(1)
            # Fallback: recognise special group objects like PipeGroup(...)
            if not type_match:
                g = group_pattern.match(entity_str)
                if g:
                    type_match = g.group(1)  # e.g., PipeGroup, ElectricityGroup

            if type_match:
                if type_match not in entity_groups:
                    entity_groups[type_match] = []
                # Clean the entity string before adding to group
                cleaned_str = clean_entity_string(entity_str)
                entity_groups[type_match].append(cleaned_str)
            else:
                # Skip entities we cannot categorise but keep a console warning for debugging
                print(
                    "[ObservationFormatter] Unable to determine type for entity:",
                    entity_str,
                )

        # Format each entity group
        group_strs = []
        for entity_type, group in sorted(entity_groups.items()):
            count = len(group)
            group_str = f"- {entity_type}: {count}"

            # Add details for each entity in the group
            if group:
                group_str += "\n" + "\n".join(f"  - {entity}" for entity in group)

            group_strs.append(group_str)

        return "### Entities\n" + "\n".join(group_strs)

    @staticmethod
    def format_flows(flows: Dict[str, Any]) -> str:
        """Format production flow information"""
        if not flows or not any(flows.values()):
            return "### Production Flows\nNone"

        flow_str = "### Production Flows\n"

        # Format input flows
        if flows.get("input"):
            flow_str += "#### Inputs\n"
            for item in flows["input"]:
                if item["rate"] > 0:
                    flow_str += f"- {item['type']}: {item['rate']:.2f}/s\n"

        # Format output flows
        if flows.get("output"):
            if flows.get("input"):
                flow_str += "\n"
            flow_str += "#### Outputs\n"
            for item in flows["output"]:
                if item["rate"] > 0:
                    flow_str += f"- {item['type']}: {item['rate']:.2f}/s\n"

        # Format crafted items
        if flows.get("crafted"):
            if flows.get("input") or flows.get("output"):
                flow_str += "\n"
            flow_str += "#### Crafted Items\n"
            for item in flows["crafted"]:
                item_name = item.get("type", "unknown")
                count = item.get("count", 1)
                flow_str += f"- {item_name}: {count}\n"

        # Format harvested items
        if flows.get("harvested"):
            if flows.get("input") or flows.get("output") or flows.get("crafted"):
                flow_str += "\n"
            flow_str += "#### Harvested Items\n"
            for item in flows["harvested"]:
                if item["amount"] > 0:
                    flow_str += f"- {item['type']}: {item['amount']:.2f}\n"

        # Format price list
        if flows.get("price_list"):
            if any(flows.get(k) for k in ["input", "output", "crafted", "harvested"]):
                flow_str += "\n"
            flow_str += "#### Price List\n"
            for item in flows["price_list"]:
                flow_str += f"- {item['type']}: {item['price']:.2f}\n"

        # Format static items
        if flows.get("static_items"):
            if any(
                flows.get(k)
                for k in ["input", "output", "crafted", "harvested", "price_list"]
            ):
                flow_str += "\n"
            flow_str += "#### Static Items\n"
            for item in flows["static_items"]:
                flow_str += f"- {item['type']}: {item['value']:.2f}\n"

        return flow_str

    @staticmethod
    def format_research(research: Dict[str, Any]) -> str:
        """Format research state information"""
        if not research:
            return "### Research\nNone"

        research_str = "### Research\n"

        # Format current research
        if research.get("current_research"):
            research_str += f"#### Current Research\n- {research['current_research']}: {research['research_progress'] * 100:.1f}%\n"

        # Format research queue
        if research.get("research_queue"):
            if research.get("current_research"):
                research_str += "\n"
            research_str += "#### Research Queue\n"
            for tech in research["research_queue"]:
                research_str += f"- {tech}\n"

        # Format technologies
        techs = research.get("technologies")
        if techs:
            # Accept both dict and list
            if isinstance(techs, list):
                # Convert list to dict using 'name' as key
                techs = {t["name"]: t for t in techs if "name" in t}
            if research.get("current_research") or research.get("research_queue"):
                research_str += "\n"
            research_str += "#### Technologies\n"
            for name, tech in techs.items():
                status = "✅" if tech.get("researched") else "⏳"
                enabled = "🔓" if tech.get("enabled") else "🔒"
                research_str += (
                    f"- {status} {enabled} {name} (Level {tech.get('level', 0)})\n"
                )
                if tech.get("prerequisites"):
                    research_str += (
                        f"  Prerequisites: {', '.join(tech['prerequisites'])}\n"
                    )
                if tech.get("ingredients"):
                    # Handle both list of dicts and dict formats
                    if isinstance(tech["ingredients"], list):
                        ingredients = ", ".join(
                            f"{ing.get('name', ing.get('item', ''))} x{ing.get('amount', ing.get('value', 0))}"
                            for ing in tech["ingredients"]
                        )
                        research_str += f"  Ingredients: {ingredients}\n"
                    else:
                        research_str += f"  Ingredients: {', '.join(f'{item} x{amount}' for item, amount in tech['ingredients'].items())}\n"
                if tech.get("research_unit_count", 0) > 0:
                    research_str += f"  Research Units: {tech['research_unit_count']} (Energy: {tech.get('research_unit_energy', 0):.1f})\n"

        return research_str

    @staticmethod
    def format_task(task: Optional[Dict[str, Any]]) -> str:
        """Format task verification information"""
        if not task:
            return ""

        status = "✅ SUCCESS" if task["success"] else "⏳ IN PROGRESS"
        task_str = f"### Task Status\n{status}\n"

        if task.get("message"):
            task_str += f"\n**Message:** {task['message']}\n"

        if task.get("meta"):
            task_str += "\n**Task Details:**\n"
            for meta_item in task["meta"]:
                task_str += f"- {meta_item['key']}: {meta_item['value']}\n"

        return task_str

    @staticmethod
    def format_messages(
        messages: List[Dict[str, Any]], last_timestamp: float = 0.0
    ) -> str:
        """Format messages from other agents"""
        if not messages:
            return ""

        # Filter messages newer than last timestamp
        new_messages = [msg for msg in messages if msg["timestamp"] > last_timestamp]

        if not new_messages:
            return ""

        # Format messages
        message_strs = ["### Messages"]
        for msg in new_messages:
            sender_info = (
                f"Agent {msg['sender']}" if msg["sender"] != "-1" else "Leader"
            )
            message_strs.append(f"- **[{sender_info}]**: {msg['content']}")

        return "\n".join(message_strs)

    @staticmethod
    def format_functions(serialized_functions: List[Dict[str, Any]]) -> str:
        """Format serialized functions into readable descriptions"""
        if not serialized_functions:
            return ""

        # Unpickle and format each function
        function_strs = ["### Available Functions"]
        for func_data in serialized_functions:
            try:
                # Unpickle the function
                pickled_data = bytes.fromhex(func_data["pickled_function"])
                func = pickle.loads(pickled_data)

                # Get formatted string representation
                function_strs.append(f"\n```python\n{func}\n```")
            except Exception as e:
                function_strs.append(
                    f"\n- {func_data['name']}: [Error unpickling function: {str(e)}]"
                )

        return "\n".join(function_strs)

    @staticmethod
    def format_raw_text(raw_text: str) -> str:
        """Format raw text output from the last action"""
        if not raw_text or raw_text.strip() == "":
            return ""

        return f"### Raw Output\n```\n{raw_text.strip()}\n```"

    def format(
        self, observation: Observation, last_message_timestamp: float = 0.0
    ) -> FormattedObservation:
        """Format a complete observation into helpful strings"""
        # Convert Observation to dict if needed
        obs_dict = observation.to_dict()

        # Format each component based on include flags
        formatted_parts = []

        if self.include_inventory:
            inventory_str = self.format_inventory(obs_dict.get("inventory", []))
            formatted_parts.append(inventory_str)

        if self.include_entities:
            entities_str = self.format_entities(obs_dict.get("entities", []))
            formatted_parts.append(entities_str)

        if self.include_flows:
            flows_str = self.format_flows(obs_dict.get("flows", {}))
            formatted_parts.append(flows_str)

        if self.include_functions:
            functions_str = self.format_functions(
                obs_dict.get("serialized_functions", [])
            )
            formatted_parts.append(functions_str)

        # Add research information
        if self.include_research:
            research_str = self.format_research(obs_dict.get("research", {}))
            formatted_parts.append(research_str)

        # Add optional components if they exist and are enabled
        if self.include_task:
            task_str = self.format_task(obs_dict.get("task_verification"))
            if task_str:
                formatted_parts.append(task_str)

        if self.include_messages:
            messages_str = self.format_messages(
                obs_dict.get("messages", []), last_message_timestamp
            )
            if messages_str:
                formatted_parts.append(messages_str)

        # Add raw text output if enabled
        if self.include_raw_output:
            raw_text_str = self.format_raw_text(obs_dict.get("raw_text", ""))
            if raw_text_str:
                formatted_parts.append(raw_text_str)

        # Combine all parts with newlines
        raw_str = "\n\n".join(formatted_parts)

        # Create FormattedObservation with all fields, even if they're empty
        return FormattedObservation(
            inventory_str=self.format_inventory(obs_dict.get("inventory", []))
            if self.include_inventory
            else "",
            entities_str=self.format_entities(obs_dict.get("entities", []))
            if self.include_entities
            else "",
            flows_str=self.format_flows(obs_dict.get("flows", {}))
            if self.include_flows
            else "",
            task_str=self.format_task(obs_dict.get("task_verification"))
            if self.include_task
            else "",
            messages_str=self.format_messages(
                obs_dict.get("messages", []), last_message_timestamp
            )
            if self.include_messages
            else "",
            functions_str=self.format_functions(
                obs_dict.get("serialized_functions", [])
            )
            if self.include_functions
            else "",
            raw_text_str=self.format_raw_text(obs_dict.get("raw_text", ""))
            if self.include_raw_output
            else "",
            raw_str=raw_str,
        )
