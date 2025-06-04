from dataclasses import dataclass
import pickle

from entities import EntityStatus, Direction
from gym_env.observation import Achievement, Observation
from typing import Any, Dict, List, Optional, Tuple, Union


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

    errors_str: str
    """Formatted string containing any error messages from the last action.
    Example:
    ### Errors
    - Invalid position for entity placement
    - Not enough resources
    Empty string if no errors occurred."""

    flows_str: str
    """Formatted string showing current production flow rates.
    Example:
    ### Production Flows
    #### Inputs
    - coal: 1.50/s
    #### Outputs
    - iron-ore: 0.75/s
    Shows both input consumption and output production rates per second."""

    achievements_str: str
    """Formatted string showing achievement progress.
    Example:
    ### Achievement Progress
    - Automated Mining: 75.0%
    Empty string if no achievements are being tracked."""

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
    [Any raw output from the last action]
    ```"""


class BasicObservationFormatter:
    """Formats gym environment observations into helpful strings"""

    def __init__(self,
                 include_inventory: bool = True,
                 include_entities: bool = True,
                 include_errors: bool = True,
                 include_flows: bool = True,
                 include_achievements: bool = True,
                 include_task: bool = True,
                 include_messages: bool = True,
                 include_functions: bool = True,
                 include_state_changes: bool = True,
                 include_raw_output: bool = True,
                 include_research: bool = True):
        """Initialize the formatter with flags for which fields to include"""
        self.include_inventory = include_inventory
        self.include_entities = include_entities
        self.include_errors = include_errors
        self.include_flows = include_flows
        self.include_achievements = include_achievements
        self.include_task = include_task
        self.include_messages = include_messages
        self.include_functions = include_functions
        self.include_state_changes = include_state_changes
        self.include_raw_output = include_raw_output
        self.include_research = include_research

    @staticmethod
    def format_inventory(inventory: Dict[str, Any]) -> str:
        """Format inventory information"""
        if not inventory:
            return "### Inventory\nEmpty"

        # Sort items by quantity for consistent output
        sorted_items = sorted(inventory.items(), key=lambda x: x[1], reverse=True)

        # Format each item
        item_strs = []
        for item_type, quantity in sorted_items:
            if quantity > 0:
                item_strs.append(f"- {item_type}: {quantity}")

        return "### Inventory\n" + "\n".join(item_strs)

    @staticmethod
    def format_entities(entities: List[Dict[str, Any]]) -> str:
        """Format entity information"""
        if not entities:
            return "### Entities\nNone found"

        # Group entities by type
        entity_groups = {}
        for entity in entities:
            entity_type = entity['type']
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(entity)

        # Format each entity group
        group_strs = []
        for entity_type, group in sorted(entity_groups.items()):
            count = len(group)
            # Get status information for the group
            statuses = {}
            for entity in group:
                status = entity.get('status', 0)
                if status not in statuses:
                    statuses[status] = 0
                statuses[status] += 1

            # Get detailed information for each entity in the group
            entity_details = []
            for entity in group:
                detail_parts = []
                
                # Basic fields
                if 'position' in entity:
                    pos = entity['position']
                    # Handle all possible position formats
                    if isinstance(pos, dict):
                        x, y = pos.get('x', 0), pos.get('y', 0)
                    elif isinstance(pos, list) and len(pos) >= 2:
                        x, y = pos[0], pos[1]
                    elif hasattr(pos, 'x') and hasattr(pos, 'y'):
                        x, y = pos.x, pos.y
                    else:
                        x, y = 0, 0  # Default values if position format is unknown
                    detail_parts.append(f"pos=({x:.1f}, {y:.1f})")
                
                if 'direction' in entity:
                    direction = Direction(entity['direction'])
                    if direction:
                        detail_parts.append(f"dir={direction.name}")
                
                if 'energy' in entity:
                    detail_parts.append(f"energy={entity['energy']:.1f}")
                
                if 'health' in entity:
                    detail_parts.append(f"health={entity['health']:.1f}")
                
                # Entity-specific fields
                if 'inventory' in entity and entity['inventory']:
                    inv_items = [f"{item}: {qty}" for item, qty in entity['inventory'].items() if qty > 0]
                    if inv_items:
                        detail_parts.append(f"inv=[{', '.join(inv_items)}]")
                
                if 'warnings' in entity and entity['warnings']:
                    detail_parts.append(f"warnings=[{', '.join(entity['warnings'])}]")
                
                # Special fields for specific entity types
                if entity_type == 'transport-belt':
                    if 'is_terminus' in entity:
                        detail_parts.append("terminus" if entity['is_terminus'] else "not_terminus")
                    if 'is_source' in entity:
                        detail_parts.append("source" if entity['is_source'] else "not_source")
                
                if entity_type == 'assembling-machine':
                    if 'recipe' in entity and entity['recipe']:
                        detail_parts.append(f"recipe={entity['recipe']}")
                
                if entity_type == 'lab':
                    if 'research' in entity and entity['research']:
                        detail_parts.append(f"research={entity['research']}")
                
                if entity_type == 'rocket-silo':
                    if 'rocket_parts' in entity:
                        detail_parts.append(f"parts={entity['rocket_parts']}")
                    if 'rocket_progress' in entity:
                        detail_parts.append(f"progress={entity['rocket_progress']:.1f}%")
                    if 'launch_count' in entity:
                        detail_parts.append(f"launches={entity['launch_count']}")
                
                if entity_type == 'electricity-pole':
                    if 'flow_rate' in entity:
                        detail_parts.append(f"flow={entity['flow_rate']:.1f}")
                
                if entity_type == 'pipe':
                    if 'fluid' in entity and entity['fluid']:
                        detail_parts.append(f"fluid={entity['fluid']}")
                    if 'flow_rate' in entity:
                        detail_parts.append(f"flow={entity['flow_rate']:.1f}")
                    if 'contents' in entity:
                        detail_parts.append(f"contents={entity['contents']:.1f}")

                # Handle entity group specific fields
                if entity_type == 'belt-group':
                    if 'belts' in entity:
                        belt_count = len(entity['belts'])
                        detail_parts.append(f"[{belt_count} belts]")
                    if 'inputs' in entity:
                        input_count = len(entity['inputs'])
                        detail_parts.append(f"inputs={input_count}")
                    if 'outputs' in entity:
                        output_count = len(entity['outputs'])
                        detail_parts.append(f"outputs={output_count}")
                    if 'inventory' in entity:
                        inv_items = [f"{item}: {qty}" for item, qty in entity['inventory'].items() if qty > 0]
                        if inv_items:
                            detail_parts.append(f"inventory=[{', '.join(inv_items)}]")

                elif entity_type == 'pipe-group':
                    if 'pipes' in entity:
                        pipe_count = len(entity['pipes'])
                        detail_parts.append(f"[{pipe_count} pipes]")
                    if 'fluid' in entity:
                        detail_parts.append(f"fluid={entity['fluid']}")
                    if 'flow_rate' in entity:
                        detail_parts.append(f"flow={entity['flow_rate']:.1f}")

                elif entity_type == 'electricity-group':
                    if 'poles' in entity:
                        pole_count = len(entity['poles'])
                        positions = [f"(x={p['position'][0]:.1f},y={p['position'][1]:.1f})" for p in entity['poles']]
                        if len(positions) > 6:
                            positions = positions[:3] + ['...'] + positions[-3:]
                        detail_parts.append(f"[{pole_count} poles: {','.join(positions)}]")
                    if 'voltage' in entity:
                        detail_parts.append(f"voltage={entity['voltage']:.1f}")

                elif entity_type == 'wall-group':
                    if 'entities' in entity:
                        wall_count = len(entity['entities'])
                        detail_parts.append(f"[{wall_count} walls]")

                # Add entity details if there are any
                if detail_parts:
                    entity_details.append(f"  - {', '.join(detail_parts)}")

            # Combine group summary with entity details
            group_str = f"- {entity_type}: {count}"
            if entity_details:
                group_str += "\n" + "\n".join(entity_details)
            group_strs.append(group_str)

        return "### Entities\n" + "\n".join(group_strs)

    @staticmethod
    def format_errors(errors: List[str]) -> str:
        """Format error information"""
        if not errors:
            return ""

        return "### Errors\n" + "\n".join(f"- {error}" for error in errors)

    @staticmethod
    def format_flows(flows: Dict[str, Any]) -> str:
        """Format production flow information"""
        if not flows or not any(flows.values()):
            return "### Production Flows\nNone"

        flow_str = "### Production Flows\n"

        # Format input flows
        if flows.get('input'):
            flow_str += "#### Inputs\n"
            for item, rate in flows['input'].items():
                if rate > 0:
                    flow_str += f"- {item}: {rate:.2f}/s\n"

        # Format output flows
        if flows.get('output'):
            if flows.get('input'):
                flow_str += "\n"
            flow_str += "#### Outputs\n"
            for item, rate in flows['output'].items():
                if rate > 0:
                    flow_str += f"- {item}: {rate:.2f}/s\n"

        # Format crafted items
        if flows.get('crafted'):
            if flows.get('input') or flows.get('output'):
                flow_str += "\n"
            flow_str += "#### Crafted Items\n"
            for item in flows['crafted']:
                # Each item in crafted is a Dict[str, Any]
                item_name = item.get('type', 'unknown')
                count = item.get('count', 1)
                flow_str += f"- {item_name}: {count}\n"

        # Format harvested items
        if flows.get('harvested'):
            if flows.get('input') or flows.get('output') or flows.get('crafted'):
                flow_str += "\n"
            flow_str += "#### Harvested Items\n"
            for item, amount in flows['harvested'].items():
                if amount > 0:
                    flow_str += f"- {item}: {amount:.2f}\n"

        # Format price list
        if flows.get('price_list'):
            if any(flows.get(k) for k in ['input', 'output', 'crafted', 'harvested']):
                flow_str += "\n"
            flow_str += "#### Price List\n"
            for item, price in flows['price_list'].items():
                flow_str += f"- {item}: {price:.2f}\n"

        # Format static items
        if flows.get('static_items'):
            if any(flows.get(k) for k in ['input', 'output', 'crafted', 'harvested', 'price_list']):
                flow_str += "\n"
            flow_str += "#### Static Items\n"
            for item, value in flows['static_items'].items():
                flow_str += f"- {item}: {value:.2f}\n"

        return flow_str

    @staticmethod
    def format_research(research: Dict[str, Any]) -> str:
        """Format research state information"""
        if not research:
            return "### Research\nNone"

        research_str = "### Research\n"

        # Format current research
        if research.get('current_research'):
            research_str += f"#### Current Research\n- {research['current_research']}: {research['research_progress']*100:.1f}%\n"

        # Format research queue
        if research.get('research_queue'):
            if research.get('current_research'):
                research_str += "\n"
            research_str += "#### Research Queue\n"
            for tech in research['research_queue']:
                research_str += f"- {tech}\n"

        # Format technologies
        if research.get('technologies'):
            if research.get('current_research') or research.get('research_queue'):
                research_str += "\n"
            research_str += "#### Technologies\n"
            for name, tech in research['technologies'].items():
                status = "✅" if tech['researched'] else "⏳"
                enabled = "🔓" if tech['enabled'] else "🔒"
                research_str += f"- {status} {enabled} {name} (Level {tech['level']})\n"
                if tech['prerequisites']:
                    research_str += f"  Prerequisites: {', '.join(tech['prerequisites'])}\n"
                if tech['ingredients']:
                    # Handle both list of dicts and dict formats
                    if isinstance(tech['ingredients'], list):
                        research_str += f"  Ingredients: {', '.join(f'{ing.get('name', '')} x{ing.get('amount', 0)}' for ing in tech['ingredients'])}\n"
                    else:
                        research_str += f"  Ingredients: {', '.join(f'{item} x{amount}' for item, amount in tech['ingredients'].items())}\n"
                if tech['research_unit_count'] > 0:
                    research_str += f"  Research Units: {tech['research_unit_count']} (Energy: {tech['research_unit_energy']:.1f})\n"

        return research_str

    @staticmethod
    def format_achievements(achievements: List[Union[Achievement, Dict[str, Any]]]) -> str:
        """Format achievement information"""
        if not achievements or not any(achievements):
            return "### Achievement Progress\nNone"

        achievement_strs = ["### Achievement Progress"]

        for achievement in achievements:
            # Handle both dictionary and Achievement object formats
            static = achievement.get('static', {}) if isinstance(achievement, dict) else achievement.static
            dynamic = achievement.get('dynamic', {}) if isinstance(achievement, dict) else achievement.dynamic

            if static:
                achievement_strs.append("\n#### Static Achievements")
                for item, value in static.items():
                    achievement_strs.append(f"- {item}: {value:.1f}")

            if dynamic:
                achievement_strs.append("\n#### Dynamic Achievements")
                for item, value in dynamic.items():
                    achievement_strs.append(f"- {item}: {value:.1f}/s")

        return "\n".join(achievement_strs)

    @staticmethod
    def format_task(task: Optional[Dict[str, Any]]) -> str:
        """Format task verification information"""
        if not task:
            return ""

        status = "✅ SUCCESS" if task['success'] else "⏳ IN PROGRESS"
        task_str = f"### Task Status\n{status}\n"

        if task.get('message'):
            task_str += f"\n**Message:** {task['message']}\n"

        if task.get('meta'):
            task_str += "\n**Task Details:**\n"
            for key, value in task['meta'].items():
                task_str += f"- {key}: {value}\n"

        return task_str

    @staticmethod
    def format_messages(messages: List[Dict[str, Any]], last_timestamp: float = 0.0) -> str:
        """Format messages from other agents"""
        if not messages:
            return ""

        # Filter messages newer than last timestamp
        new_messages = [
            msg for msg in messages
            if msg['timestamp'] > last_timestamp
        ]

        if not new_messages:
            return ""

        # Format messages
        message_strs = ["### Messages"]
        for msg in new_messages:
            sender_info = f"Agent {msg['sender']}" if msg['sender'] != "-1" else "Leader"
            message_strs.append(f"- **[{sender_info}]**: {msg['content']}")

        return "\n".join(message_strs)

    @staticmethod
    def format_state_changes(changes: Dict[str, Any]) -> str:
        """Format state change information"""
        if not changes or not any(changes.values()):
            return "### State Changes\nNone"

        change_strs = ["### State Changes"]

        # Format entity changes
        if changes.get('entity_changes'):
            change_strs.append("\n**Entity Changes:**")
            for change in changes['entity_changes']:
                sign = "+" if change['change'] > 0 else ""
                change_strs.append(f"- {change['entity']}: {sign}{change['change']}")

        # Format inventory changes
        if changes.get('inventory_changes'):
            change_strs.append("\n**Inventory Changes:**")
            for change in changes['inventory_changes']:
                sign = "+" if change['change'] > 0 else ""
                if change['change'] == 0:
                    continue
                change_strs.append(f"- {change['item']}: {sign}{change['change']}")

        return "\n".join(change_strs)

    @staticmethod
    def format_functions(serialized_functions: List[Dict[str, Any]]) -> str:
        """Format serialized functions into readable descriptions"""
        if not serialized_functions:
            return "### Available Functions\nNone"

        # Unpickle and format each function
        function_strs = ["### Available Functions"]
        for func_data in serialized_functions:
            try:
                # Unpickle the function
                pickled_data = bytes.fromhex(func_data['pickled_function'])
                func = pickle.loads(pickled_data)

                # Get formatted string representation
                function_strs.append(f"\n```python\n{func}\n```")
            except Exception as e:
                function_strs.append(f"\n- {func_data['name']}: [Error unpickling function: {str(e)}]")

        return "\n".join(function_strs)

    def format(self, observation: Observation, last_message_timestamp: float = 0.0) -> FormattedObservation:
        """Format a complete observation into helpful strings"""
        # Convert Observation to dict if needed
        obs_dict = observation.to_dict()

        # Format each component based on include flags
        formatted_parts = []

        if self.include_inventory:
            assert isinstance(obs_dict.get('inventory', {}), dict), obs_dict.get('inventory', {})
            inventory_str = self.format_inventory(obs_dict.get('inventory', {}))
            formatted_parts.append(inventory_str)

        if self.include_entities:
            entities_str = self.format_entities(obs_dict.get('entities', []))
            formatted_parts.append(entities_str)

        if self.include_flows:
            flows_str = self.format_flows(obs_dict.get('flows', {}))
            formatted_parts.append(flows_str)

        if self.include_functions:
            functions_str = self.format_functions(obs_dict.get('serialized_functions', []))
            formatted_parts.append(functions_str)

        # Add research information
        if self.include_research:
            research_str = self.format_research(obs_dict.get('research', {}))
            formatted_parts.append(research_str)

        # Add optional components if they exist and are enabled
        if self.include_errors:
            errors_str = self.format_errors(obs_dict.get('errors', []))
            if errors_str:
                formatted_parts.append(errors_str)

        if self.include_achievements:
            achievements_str = self.format_achievements(obs_dict.get('achievements', []))
            if achievements_str:
                formatted_parts.append(achievements_str)

        if self.include_task:
            task_str = self.format_task(obs_dict.get('task_verification'))
            if task_str:
                formatted_parts.append(task_str)

        if self.include_messages:
            messages_str = self.format_messages(obs_dict.get('messages', []), last_message_timestamp)
            if messages_str:
                formatted_parts.append(messages_str)

        if self.include_state_changes:
            state_changes = self.format_state_changes(obs_dict.get('state_changes', {}))
            if state_changes:
                formatted_parts.append(state_changes)

        if self.include_raw_output:
            raw_str = obs_dict.get('raw_text', '')
            if raw_str:
                formatted_parts.append(f"### Raw Output\n```\n{raw_str}\n```")

        # Combine all parts with newlines
        raw_str = "\n\n".join(formatted_parts)

        # Create FormattedObservation with all fields, even if they're empty
        return FormattedObservation(
            inventory_str=self.format_inventory(obs_dict.get('inventory', {})) if self.include_inventory else "",
            entities_str=self.format_entities(obs_dict.get('entities', [])) if self.include_entities else "",
            errors_str=self.format_errors(obs_dict.get('errors', [])) if self.include_errors else "",
            flows_str=self.format_flows(obs_dict.get('flows', {})) if self.include_flows else "",
            achievements_str=self.format_achievements(obs_dict.get('achievements', [])) if self.include_achievements else "",
            task_str=self.format_task(obs_dict.get('task_verification')) if self.include_task else "",
            messages_str=self.format_messages(obs_dict.get('messages', []), last_message_timestamp) if self.include_messages else "",
            functions_str=self.format_functions(obs_dict.get('serialized_functions', [])) if self.include_functions else "",
            raw_str=raw_str
        )