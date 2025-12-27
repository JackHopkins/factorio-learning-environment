import pickle
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from fle.commons.constants import REWARD_OVERRIDE_KEY
from fle.env.gym_env.observation import Observation


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

    task_info_str: str
    """Formatted string showing task information and objectives.
    Example:
    ### Task Information
    **Goal:** Create automatic iron ore factory
    **Agent Instructions:** You are the mining specialist
    **Task Key:** iron_ore_automation"""

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

    game_info_str: str
    """Formatted string showing game timing information.
    Example:
    ### Game Info
    - Elapsed Time: 1:00:00
    - Ticks: 3600
    Shows elapsed time in hours:minutes:seconds format and current game tick count."""

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

    ### Game Info
    - Elapsed Time: 1:00:00
    - Ticks: 3600

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
        include_game_info: bool = True,
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
        self.include_game_info = include_game_info

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
            entity_str = entity_str.replace("class 'fle.env.entities.", "")
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

        flow_str = "### Production Flows (for *entire* previous step)\n"

        # Build harvested lookup to subtract from production
        harvested_by_type = {}
        for item in flows.get("harvested", []):
            harvested_by_type[item["type"]] = item.get("amount", 0)

        # Format input flows
        if flows.get("input"):
            flow_str += "#### Inputs\n"
            for item in flows["input"]:
                if item["rate"] > 0:
                    flow_str += f"- {item['type']}: {item['rate']:.2f}\n"

        # Format output flows (subtract harvested since production includes both automated and harvested)
        if flows.get("output"):
            if flows.get("input"):
                flow_str += "\n"
            flow_str += "#### Outputs\n"
            for item in flows["output"]:
                # Subtract harvested amount from production
                harvested_amount = harvested_by_type.get(item["type"], 0)
                adjusted_rate = item["rate"] - harvested_amount
                if adjusted_rate > 0:
                    flow_str += f"- {item['type']}: {adjusted_rate:.2f}\n"

        # Format crafted items
        if flows.get("crafted"):
            if flows.get("input") or flows.get("output"):
                flow_str += "\n"
            flow_str += "#### Crafted Items\n"
            for item in flows["crafted"]:
                # Crafted items have structure: {"crafted_count": N, "inputs": {...}, "outputs": {...}}
                # Display the outputs (what was crafted) with the count
                crafted_count = item.get("crafted_count", 1)
                outputs = item.get("outputs", {})
                if outputs:
                    for output_name, output_amount in outputs.items():
                        flow_str += f"- {output_name}: {output_amount} (crafted {crafted_count}x)\n"
                else:
                    # Fallback for legacy format with "type" field
                    item_name = item.get("type", "unknown")
                    count = item.get("count", 1)
                    if item_name != "unknown":
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
    def format_flows_compact(flows: Dict[str, Any]) -> str:
        """Format production flows into compact sub-bullets.

        Args:
            flows: Dict with keys 'input', 'output', 'crafted', 'harvested'
                  - input: list of {"type": str, "rate": float} (consumed items)
                  - output: list of {"type": str, "rate": float} (produced items)
                  - crafted: list of crafted item dicts
                  - harvested: list of {"type": str, "amount": float}

        Returns:
            Formatted string with sub-bullets for each flow type
        """
        lines = []

        # Build harvested lookup to subtract from production
        harvested_by_type = {}
        for item in flows.get("harvested", []):
            harvested_by_type[item["type"]] = item.get("amount", 0)

        # Consumed (input)
        consumed = flows.get("input", [])
        if consumed:
            items = ", ".join(
                f"{item['type']}: {item['rate']:.1f}"
                for item in consumed
                if item.get("rate", 0) > 0
            )
            lines.append(f"  - Consumed: {items}" if items else "  - Consumed: none")
        else:
            lines.append("  - Consumed: none")

        # Produced (output) - subtract harvested since production includes both automated and harvested
        produced = flows.get("output", [])
        if produced:
            adjusted_items = []
            for item in produced:
                harvested_amount = harvested_by_type.get(item["type"], 0)
                adjusted_rate = item.get("rate", 0) - harvested_amount
                if adjusted_rate > 0:
                    adjusted_items.append(f"{item['type']}: {adjusted_rate:.1f}")
            items = ", ".join(adjusted_items)
            lines.append(f"  - Produced: {items}" if items else "  - Produced: none")
        else:
            lines.append("  - Produced: none")

        # Crafted
        crafted = flows.get("crafted", [])
        if crafted:
            crafted_items = []
            for item in crafted:
                count = item.get("crafted_count", 1)
                outputs = item.get("outputs", {})
                for name, amount in outputs.items():
                    crafted_items.append(f"{name}: {amount} (x{count})")
            if crafted_items:
                lines.append(f"  - Crafted: {', '.join(crafted_items)}")
            else:
                lines.append("  - Crafted: none")
        else:
            lines.append("  - Crafted: none")

        # Harvested
        harvested = flows.get("harvested", [])
        if harvested:
            items = ", ".join(
                f"{item['type']}: {item['amount']:.1f}"
                for item in harvested
                if item.get("amount", 0) > 0
            )
            lines.append(f"  - Harvested: {items}" if items else "  - Harvested: none")
        else:
            lines.append("  - Harvested: none")

        return "\n".join(lines)

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
    def format_game_info(
        game_info: Dict[str, Any],
        score: float = 0.0,
        automated_score: float = 0.0,
    ) -> str:
        """Format game timing and score information"""
        if not game_info:
            return "### Game Info\nNo game information available"

        info_str = "### Game Info\n"

        # Add elapsed time information in H:M:S format
        if "time" in game_info:
            total_seconds = int(game_info["time"])
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            info_str += f"- Elapsed Time: {hours:d}:{minutes:02d}:{seconds:02d}\n"

        # Add tick information
        if "tick" in game_info:
            info_str += f"- Ticks: {game_info['tick']}\n"

        # Add score information
        info_str += f"- Production Score: {score:.1f}\n"
        info_str += f"- Automated Score: {automated_score:.1f}\n"

        return info_str

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
                if meta_item["key"] == REWARD_OVERRIDE_KEY:
                    continue
                task_str += f"- {meta_item['key']}: {meta_item['value']}\n"

        return task_str

    @staticmethod
    def format_task_info(task_info: Optional[Dict[str, Any]]) -> str:
        """Format task information"""
        if not task_info:
            return ""

        info_str = "### Task Information\n"

        if task_info.get("goal_description"):
            info_str += f"**Goal:** {task_info['goal_description']}\n"

        if task_info.get("agent_instructions"):
            info_str += f"**Agent Instructions:** {task_info['agent_instructions']}\n"

        if task_info.get("task_key"):
            info_str += f"**Task Key:** {task_info['task_key']}\n"

        if task_info.get("trajectory_length"):
            info_str += f"**Trajectory Length:** {task_info['trajectory_length']}\n"

        return info_str

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

        # Add game info
        if self.include_game_info:
            game_info_str = self.format_game_info(
                obs_dict.get("game_info", {}),
                score=obs_dict.get("score", 0.0),
                automated_score=obs_dict.get("automated_score", 0.0),
            )
            formatted_parts.append(game_info_str)

        # Add optional components if they exist and are enabled
        if self.include_task:
            task_str = self.format_task(obs_dict.get("task_verification"))
            if task_str:
                formatted_parts.append(task_str)

            task_info_str = self.format_task_info(obs_dict.get("task_info"))
            if task_info_str:
                formatted_parts.append(task_info_str)

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
            task_info_str=self.format_task_info(obs_dict.get("task_info"))
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
            game_info_str=self.format_game_info(
                obs_dict.get("game_info", {}),
                score=obs_dict.get("score", 0.0),
                automated_score=obs_dict.get("automated_score", 0.0),
            )
            if self.include_game_info
            else "",
            raw_text_str=self.format_raw_text(obs_dict.get("raw_text", ""))
            if self.include_raw_output
            else "",
            raw_str=raw_str,
        )


class TreeObservationFormatter(BasicObservationFormatter):
    """Formats observations using a prefix trie structure for token efficiency.

    Groups entities by type, then builds a trie based on shared key-value pairs.
    Shared attributes appear at branch nodes, unique attributes at leaves.
    Keys that vary vs are shared are computed dynamically from the actual data.

    Example output for 3 inserters with same direction but different positions:
        - inserter: 3
          [direction=SOUTH, status=WORKING, width=1, height=1]
            - position=(5.5, 3.5), drop_position=(5.5, 2.5)
            - position=(7.5, 3.5), drop_position=(7.5, 2.5)
            - position=(9.5, 3.5), drop_position=(9.5, 2.5)

    Args:
        excluded_keys: Optional set of keys to exclude from output entirely.
                      Defaults to empty set (include all keys).
    """

    def __init__(self, excluded_keys: Optional[set] = None, **kwargs):
        """Initialize the TreeObservationFormatter.

        Args:
            excluded_keys: Set of keys to exclude from output. Defaults to None (no exclusions).
            **kwargs: Additional arguments passed to BasicObservationFormatter.
        """
        super().__init__(**kwargs)
        self.excluded_keys = excluded_keys or set()

    @staticmethod
    def parse_entity_to_dict(entity_str: str) -> Dict[str, str]:
        """Parse an entity string into a dictionary of key-value pairs.

        Handles nested structures like Position(x=1.5, y=2.5), dicts, and lists correctly.
        """
        result = {}

        # Remove class wrapper if present: "ClassName(...)" -> content inside parens
        # Match patterns like "Inserter(...)" or "\n\tInserter(...)" or "AssemblingMachine1(...)"
        # Handle both escaped \\n\\t and actual whitespace
        class_match = re.match(
            r"^[\s\\nt]*([A-Za-z][A-Za-z0-9]*)\((.*)\)$", entity_str.strip(), re.DOTALL
        )
        if class_match:
            entity_str = class_match.group(2)

        # Parse key=value pairs, handling nested structures
        current_key = ""
        current_value = ""
        bracket_depth = 0  # []
        paren_depth = 0  # ()
        brace_depth = 0  # {}
        in_key = True
        in_quotes = False
        quote_char = None

        i = 0
        while i < len(entity_str):
            char = entity_str[i]

            # Track quotes - check for escaped quotes
            if char in "'\"" and (i == 0 or entity_str[i - 1] != "\\"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None

            # Track brackets, parens, and braces (only if not in quotes)
            if not in_quotes:
                if char == "[":
                    bracket_depth += 1
                elif char == "]":
                    bracket_depth -= 1
                elif char == "(":
                    paren_depth += 1
                elif char == ")":
                    paren_depth -= 1
                elif char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth -= 1

            # At top level (not inside any nested structure)
            at_top_level = (
                bracket_depth == 0
                and paren_depth == 0
                and brace_depth == 0
                and not in_quotes
            )

            # Key-value separator (only at top level)
            if char == "=" and in_key and at_top_level:
                in_key = False
                i += 1
                continue

            # Entry separator (comma at top level)
            if char == "," and at_top_level:
                if current_key.strip():
                    result[current_key.strip()] = current_value.strip()
                current_key = ""
                current_value = ""
                in_key = True
                i += 1
                # Skip whitespace after comma
                while i < len(entity_str) and entity_str[i] in " \t\n":
                    i += 1
                continue

            # Accumulate characters
            if in_key:
                current_key += char
            else:
                current_value += char

            i += 1

        # Don't forget the last pair
        if current_key.strip():
            result[current_key.strip()] = current_value.strip()

        return result

    @staticmethod
    def format_value(_key: str, value: str) -> str:
        """Format a value for display, cleaning up common patterns."""
        value = value.strip()

        # Clean Position values
        if "Position" in value:
            x_match = re.search(r"x=([\d.-]+)", value)
            y_match = re.search(r"y=([\d.-]+)", value)
            if x_match and y_match:
                x = float(x_match.group(1))
                y = float(y_match.group(1))
                return f"({x:.1f}, {y:.1f})"

        # Clean Direction enum
        if value.startswith("<Direction.") or value.startswith("Direction."):
            dir_match = re.search(r"Direction\.(\w+)", value)
            if dir_match:
                return dir_match.group(1)

        # Clean EntityStatus enum
        if value.startswith("<EntityStatus.") or value.startswith("EntityStatus."):
            status_match = re.search(r"EntityStatus\.(\w+)", value)
            if status_match:
                return status_match.group(1)

        # Clean Prototype
        if "Prototype" in value:
            proto_match = re.search(r"<Prototype\.([^:>]+)[:>]?", value)
            if proto_match:
                return f"Prototype.{proto_match.group(1)}"
            alt_match = re.search(r"Prototype\.([A-Za-z0-9_-]+)", value)
            if alt_match:
                return f"Prototype.{alt_match.group(1)}"

        # Clean Inventory repr
        if value.startswith("Inventory("):
            # Empty inventory
            if value == "Inventory()":
                return "[]"
            # Try to extract contents
            inner_match = re.match(r"Inventory\((.*)\)", value, re.DOTALL)
            if inner_match:
                return f"[{inner_match.group(1)}]"

        # Format inventory/item lists compactly: [{'name': 'coal', 'count': 18}] -> coal:18
        if (
            value.startswith("[")
            and "'name'" in value
            and ("'count'" in value or "'amount'" in value)
        ):
            try:
                # Try to parse as Python literal and format compactly
                import ast

                items = ast.literal_eval(value)
                if isinstance(items, list) and items:
                    formatted_items = []
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", item.get("type", "?"))
                            count = item.get(
                                "count", item.get("amount", item.get("value", 0))
                            )
                            formatted_items.append(f"{name}:{count}")
                    if formatted_items:
                        return "[" + ", ".join(formatted_items) + "]"
            except (ValueError, SyntaxError):
                pass  # Fall through to return original value

        # Format recipe dicts compactly: {'category': 'smelting', ...} -> extract key info
        if value.startswith("{") and "'category'" in value:
            try:
                import ast

                recipe = ast.literal_eval(value)
                if isinstance(recipe, dict):
                    # Extract key recipe info
                    parts = []
                    if recipe.get("category"):
                        parts.append(recipe["category"])
                    # Get inputs
                    ingredients = recipe.get("ingredients", [])
                    if ingredients:
                        ing_names = [
                            i.get("name", "?")
                            for i in ingredients
                            if isinstance(i, dict)
                        ]
                        if ing_names:
                            parts.append(f"in:{'+'.join(ing_names)}")
                    # Get outputs
                    products = recipe.get("products", [])
                    if products:
                        prod_names = [
                            p.get("name", "?") for p in products if isinstance(p, dict)
                        ]
                        if prod_names:
                            parts.append(f"out:{'+'.join(prod_names)}")
                    if parts:
                        return "{" + ", ".join(parts) + "}"
            except (ValueError, SyntaxError):
                pass  # Fall through to return original value

        # Try to format as number
        try:
            num = float(value)
            if num == int(num):
                return str(int(num))
            return f"{num:.1f}"
        except ValueError:
            pass

        # Remove quotes from simple strings
        if (value.startswith("'") and value.endswith("'")) or (
            value.startswith('"') and value.endswith('"')
        ):
            return value[1:-1]

        return value

    @classmethod
    def build_entity_trie(
        cls, entities: List[Dict[str, str]], excluded_keys: Optional[set] = None
    ) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        """Build a trie structure from a list of entity dictionaries.

        Dynamically determines which keys are shared (same value across all entities)
        vs which vary (different values per entity).

        Args:
            entities: List of parsed entity dictionaries
            excluded_keys: Optional set of keys to exclude from output

        Returns:
            Tuple of (shared_attributes, list_of_unique_attributes)
            - shared_attributes: dict of key-value pairs common to ALL entities
            - unique_attributes: list of dicts with per-entity unique attributes
        """
        excluded = excluded_keys or set()

        if not entities:
            return {}, []

        if len(entities) == 1:
            # Single entity - format all non-excluded keys as unique
            unique = {}
            for key, value in entities[0].items():
                if key not in excluded:
                    unique[key] = cls.format_value(key, value)
            return {}, [unique]

        # Find keys present in all entities
        all_keys = set(entities[0].keys())
        for entity in entities[1:]:
            all_keys &= set(entity.keys())

        # Remove excluded keys
        all_keys -= excluded

        # Dynamically determine shared vs varying keys by checking actual values
        shared = {}
        varying_keys = set()

        for key in all_keys:
            values = [e.get(key, "") for e in entities]
            unique_values = set(values)

            if len(unique_values) == 1 and values[0]:
                # All entities have the same non-empty value - this is a shared key
                shared[key] = cls.format_value(key, values[0])
            else:
                # Values differ across entities - this is a varying key
                varying_keys.add(key)

        # Build unique attributes for each entity (only varying keys + keys not in all entities)
        unique_list = []
        for entity in entities:
            unique = {}
            for key, value in entity.items():
                if key in excluded:
                    continue
                if key not in shared:
                    # This key either varies or isn't present in all entities
                    unique[key] = cls.format_value(key, value)
            unique_list.append(unique)

        return shared, unique_list

    @classmethod
    def build_nested_trie(
        cls,
        entities: List[Dict[str, str]],
        excluded_keys: Optional[set] = None,
        depth: int = 0,
        max_depth: int = 5,
    ) -> dict:
        """Build a nested trie structure that groups entities by shared varying values.

        Recursively groups entities: first extracts universally shared attributes,
        then groups remaining entities by the most common varying attribute value,
        and recurses on each subgroup.

        Args:
            entities: List of parsed entity dictionaries
            excluded_keys: Optional set of keys to exclude from output
            depth: Current recursion depth
            max_depth: Maximum recursion depth to prevent infinite loops

        Returns:
            Dict with structure:
            {
                'shared': {key: value, ...},  # Attributes shared by ALL entities at this level
                'children': [
                    {'shared': {...}, 'children': [...], 'leaves': [...]},  # Subgroups
                    ...
                ],
                'leaves': [{...}, {...}]  # Individual entity unique attributes (terminal)
            }
        """
        excluded = excluded_keys or set()

        if not entities:
            return {"shared": {}, "children": [], "leaves": []}

        if len(entities) == 1:
            # Single entity - all non-excluded keys become a leaf
            unique = {}
            for key, value in entities[0].items():
                if key not in excluded:
                    unique[key] = cls.format_value(key, value)
            return {"shared": {}, "children": [], "leaves": [unique]}

        # Find keys present in all entities
        all_keys = set(entities[0].keys())
        for entity in entities[1:]:
            all_keys &= set(entity.keys())
        all_keys -= excluded

        # Determine shared vs varying keys
        shared = {}
        varying_keys = []

        for key in all_keys:
            values = [e.get(key, "") for e in entities]
            unique_values = set(values)

            if len(unique_values) == 1 and values[0]:
                shared[key] = cls.format_value(key, values[0])
            else:
                # Track varying keys with their number of unique values
                varying_keys.append((key, len(unique_values), unique_values))

        # If no varying keys or max depth reached, return leaves
        if not varying_keys or depth >= max_depth:
            leaves = []
            for entity in entities:
                unique = {}
                for key, value in entity.items():
                    if key in excluded or key in shared:
                        continue
                    unique[key] = cls.format_value(key, value)
                leaves.append(unique)
            return {"shared": shared, "children": [], "leaves": leaves}

        # Sort varying keys by number of unique values (ascending) - fewer unique values = better for grouping
        varying_keys.sort(key=lambda x: x[1])

        # Try to find a good grouping key (one with few unique values but > 1)
        # Prefer keys that create meaningful subgroups (not too many, not just 1)
        best_group_key = None
        for key, num_unique, unique_vals in varying_keys:
            if 2 <= num_unique <= len(entities) // 2 + 1:
                best_group_key = key
                break

        # If no good grouping key found, just return leaves
        if best_group_key is None:
            leaves = []
            for entity in entities:
                unique = {}
                for key, value in entity.items():
                    if key in excluded or key in shared:
                        continue
                    unique[key] = cls.format_value(key, value)
                leaves.append(unique)
            return {"shared": shared, "children": [], "leaves": leaves}

        # Group entities by the best grouping key
        groups: Dict[str, List[Dict[str, str]]] = {}
        for entity in entities:
            group_value = entity.get(best_group_key, "")
            formatted_value = cls.format_value(best_group_key, group_value)
            if formatted_value not in groups:
                groups[formatted_value] = []
            groups[formatted_value].append(entity)

        # Build children by recursing on each group
        children = []
        # Pass parent's shared keys as exclusions to children
        child_excluded = excluded | set(shared.keys())
        for group_value, group_entities in sorted(groups.items()):
            # Remove the grouping key from entities before recursing
            sub_entities = []
            for entity in group_entities:
                sub_entity = {k: v for k, v in entity.items() if k != best_group_key}
                sub_entities.append(sub_entity)

            child_trie = cls.build_nested_trie(
                sub_entities,
                excluded_keys=child_excluded,
                depth=depth + 1,
                max_depth=max_depth,
            )
            # Add the grouping key-value to the child's shared attributes
            child_trie["shared"] = {best_group_key: group_value, **child_trie["shared"]}
            child_trie["count"] = len(group_entities)
            children.append(child_trie)

        return {"shared": shared, "children": children, "leaves": []}

    @classmethod
    def format_trie_output(
        cls,
        entity_type: str,
        count: int,
        shared: Dict[str, str],
        unique_list: List[Dict[str, str]],
        indent: str = "  ",
    ) -> str:
        """Format the flat trie structure as a string (non-nested version)."""
        # Header with count
        lines = [f"- {entity_type}: {count}"]

        # Shared attributes (if any)
        if shared:
            shared_str = ", ".join(f"{k}={v}" for k, v in sorted(shared.items()))
            lines.append(f"{indent}[{shared_str}]")

        # Unique attributes per entity
        for unique in unique_list:
            if unique:
                unique_str = ", ".join(f"{k}={v}" for k, v in sorted(unique.items()))
                lines.append(f"{indent}{indent}- {unique_str}")
            else:
                lines.append(f"{indent}{indent}- (no unique attributes)")

        return "\n".join(lines)

    @classmethod
    def format_nested_trie_output(
        cls,
        trie: dict,
        indent_level: int = 1,
        indent: str = "\t",
        parent_shared_keys: Optional[set] = None,
    ) -> List[str]:
        """Format a nested trie structure as lines of text.

        Args:
            trie: The trie dict with 'shared', 'children', 'leaves', and optionally 'count'
            indent_level: Current indentation level
            indent: Indentation string (default tab)
            parent_shared_keys: Keys already shown at parent level (to avoid redundancy)

        Returns:
            List of formatted lines
        """
        lines = []
        current_indent = indent * indent_level
        parent_keys = parent_shared_keys or set()

        # Get only the NEW shared attributes (not already shown at parent level)
        shared = trie.get("shared", {})
        new_shared = {k: v for k, v in shared.items() if k not in parent_keys}

        # Collect all keys shown so far (parent + this level)
        all_shown_keys = parent_keys | set(shared.keys())

        # Format shared attributes for this level (only new ones)
        if new_shared:
            shared_str = ", ".join(f"{k}={v}" for k, v in sorted(new_shared.items()))
            count_str = f": {trie['count']}" if "count" in trie else ""
            lines.append(f"{current_indent}[{shared_str}]{count_str}")

            # Children and leaves are nested under this branch
            child_indent_level = indent_level + 1
        else:
            # No new shared attributes at this level, don't add extra indentation
            child_indent_level = indent_level

        # Recursively format children
        for child in trie.get("children", []):
            child_lines = cls.format_nested_trie_output(
                child, child_indent_level, indent, parent_shared_keys=all_shown_keys
            )
            lines.extend(child_lines)

        # Format leaf nodes (individual entities) - exclude keys already shown
        leaf_indent = indent * child_indent_level
        for leaf in trie.get("leaves", []):
            if leaf:
                filtered_leaf = {
                    k: v for k, v in leaf.items() if k not in all_shown_keys
                }
                if filtered_leaf:
                    leaf_str = ", ".join(
                        f"{k}={v}" for k, v in sorted(filtered_leaf.items())
                    )
                    lines.append(f"{leaf_indent}- {leaf_str}")

        return lines

    # Default keys to exclude from entity output (internal/unimportant fields)
    DEFAULT_EXCLUDED_KEYS = {
        # "dimensions",
        "prototype",
        "type",
        # "health",
        "game",
        "id",
        # "tile_dimensions",
        "energy",
        "warnings",
        # "electrical_id",
    }

    @classmethod
    def format_value_from_object(cls, key: str, value: Any) -> str:
        """Format a Python object value for display.

        Args:
            key: The attribute name
            value: The Python object value

        Returns:
            Formatted string representation
        """
        from fle.env.entities import Position, Direction, EntityStatus, Inventory

        # Handle None
        if value is None:
            return "None"

        # Handle Position objects
        if isinstance(value, Position):
            return f"({value.x:.1f}, {value.y:.1f})"

        # Handle Direction enum
        if isinstance(value, Direction):
            return value.name

        # Handle EntityStatus enum
        if isinstance(value, EntityStatus):
            return value.name

        # Handle Inventory objects
        if isinstance(value, Inventory):
            items = dict(value)
            if not items:
                return "[]"
            item_strs = [f"{k}:{v}" for k, v in items.items() if v > 0]
            return "[" + ", ".join(item_strs) + "]" if item_strs else "[]"

        # Handle other enums
        if hasattr(value, "name") and hasattr(value, "value"):
            return value.name

        # Handle lists
        if isinstance(value, list):
            if not value:
                return "[]"
            # Format list items
            formatted_items = [
                cls.format_value_from_object(key, item) for item in value
            ]
            return "[" + ", ".join(formatted_items) + "]"

        # Handle dicts (like recipes)
        if isinstance(value, dict):
            if not value:
                return "{}"
            # Check if it's a recipe-like dict
            if "category" in value:
                parts = []
                if value.get("category"):
                    parts.append(str(value["category"]))
                ingredients = value.get("ingredients", [])
                if ingredients:
                    ing_names = [
                        i.get("name", "?") for i in ingredients if isinstance(i, dict)
                    ]
                    if ing_names:
                        parts.append(f"in:{'+'.join(ing_names)}")
                products = value.get("products", [])
                if products:
                    prod_names = [
                        p.get("name", "?") for p in products if isinstance(p, dict)
                    ]
                    if prod_names:
                        parts.append(f"out:{'+'.join(prod_names)}")
                if parts:
                    return "{" + ", ".join(parts) + "}"
            # Generic dict formatting
            return str(value)

        # Handle floats
        if isinstance(value, float):
            if value == int(value):
                return str(int(value))
            return f"{value:.1f}"

        # Handle ints
        if isinstance(value, int):
            return str(value)

        # Handle strings - remove quotes
        if isinstance(value, str):
            return value

        # Fallback to string representation
        return str(value)

    @classmethod
    def entity_dict_to_formatted(
        cls, entity_dict: Dict[str, Any], excluded_keys: Optional[set] = None
    ) -> Dict[str, str]:
        """Convert an entity dict (from Pydantic __dict__) to a formatted dict.

        Args:
            entity_dict: Raw entity dictionary from Pydantic __dict__
            excluded_keys: Keys to exclude from output

        Returns:
            Dict with string keys and formatted string values
        """
        excluded = excluded_keys or cls.DEFAULT_EXCLUDED_KEYS
        result = {}

        for key, value in entity_dict.items():
            # Remove leading underscore from Pydantic internal fields
            clean_key = key.lstrip("_")

            # Skip excluded keys
            if clean_key in excluded:
                continue

            # Skip private attributes
            if clean_key.startswith("__"):
                continue

            # Format the value
            result[clean_key] = cls.format_value_from_object(clean_key, value)

        return result

    @classmethod
    def format_entities(
        cls, entities: List[Any], excluded_keys: Optional[set] = None
    ) -> str:
        """Format entity information using nested trie-based compression.

        Args:
            entities: List of entity dicts (from Pydantic __dict__) or strings
            excluded_keys: Optional set of keys to exclude from output

        Returns:
            Formatted string with entities grouped by type and compressed using nested trie structure
        """
        if not entities:
            return "### Entities\nNone found"

        excluded = (
            excluded_keys if excluded_keys is not None else cls.DEFAULT_EXCLUDED_KEYS
        )

        # Group entities by type (name field)
        entity_groups: Dict[str, List[Dict[str, str]]] = {}

        for entity in entities:
            # Handle both dict and string formats for backwards compatibility
            if isinstance(entity, dict):
                # Get entity name for grouping
                entity_name = entity.get("name") or entity.get("_name") or "unknown"
                if hasattr(entity_name, "lstrip"):
                    entity_name = entity_name.lstrip("_")

                # Convert to formatted dict
                formatted = cls.entity_dict_to_formatted(entity, excluded)

                if entity_name not in entity_groups:
                    entity_groups[entity_name] = []
                entity_groups[entity_name].append(formatted)
            elif isinstance(entity, str):
                # Legacy string format - parse it
                name_pattern = re.compile(r"\bname\s*=\s*'?\"?([A-Za-z0-9_-]+)'?\"?")
                n = name_pattern.search(entity)
                entity_name = n.group(1) if n else "unknown"

                parsed = cls.parse_entity_to_dict(entity)
                # Format the parsed values
                formatted = {}
                for k, v in parsed.items():
                    if k not in excluded:
                        formatted[k] = cls.format_value(k, v)

                if entity_name not in entity_groups:
                    entity_groups[entity_name] = []
                entity_groups[entity_name].append(formatted)

        # Format each entity group using nested trie structure
        group_strs = []
        for entity_type, group in sorted(entity_groups.items()):
            count = len(group)

            # Build nested trie structure (group is already list of formatted dicts)
            trie = cls.build_nested_trie(
                group, excluded_keys=set()
            )  # Already excluded above

            # Format the header
            lines = [f"- {entity_type}: {count}"]

            # Collect top-level shared keys
            top_shared = trie.get("shared", {})
            top_shared_keys = set(top_shared.keys())

            # Determine starting indent level for children
            if top_shared:
                # Format top-level shared attributes
                shared_str = ", ".join(
                    f"{k}={v}" for k, v in sorted(top_shared.items())
                )
                lines.append(f"\t[{shared_str}]")
                # Children start at indent level 2 (nested under the shared attributes)
                child_start_level = 2
            else:
                # No top-level shared, children start at indent level 1
                child_start_level = 1

            # Format children (nested groups) - pass top-level shared keys to avoid redundancy
            for child in trie.get("children", []):
                child_lines = cls.format_nested_trie_output(
                    child,
                    indent_level=child_start_level,
                    indent="\t",
                    parent_shared_keys=top_shared_keys,
                )
                lines.extend(child_lines)

            # Format leaves (individual entities at top level) - exclude top-level shared keys
            leaf_indent = "\t" * child_start_level
            for leaf in trie.get("leaves", []):
                if leaf:
                    filtered_leaf = {
                        k: v for k, v in leaf.items() if k not in top_shared_keys
                    }
                    if filtered_leaf:
                        leaf_str = ", ".join(
                            f"{k}={v}" for k, v in sorted(filtered_leaf.items())
                        )
                        lines.append(f"{leaf_indent}- {leaf_str}")

            group_strs.append("\n".join(lines))

        return "### Entities\n" + "\n".join(group_strs)
