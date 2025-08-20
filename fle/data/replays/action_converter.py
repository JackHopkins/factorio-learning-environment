"""
Handles conversion between different action argument formats.
"""

import json
import re
import ast
from typing import Dict, Any, List

from fle.env.entities import Position, Direction, PlaceholderEntity
from fle.env.game_types import prototype_by_name, Technology


class ActionConverter:
    """Handles conversion between different action argument formats."""

    @staticmethod
    def parse_function_call(call_string: str) -> tuple[str, Dict[str, Any]]:
        """Parse a function call string into function name and arguments."""
        # Extract function name and arguments using regex
        match = re.match(r"(\w+)\((.*)\)", call_string)
        if not match:
            raise ValueError(f"Invalid function call format: {call_string}")

        func_name = match.group(1)
        args_string = match.group(2)

        # Parse arguments
        args = {}
        if args_string.strip():
            # Split arguments by comma, but handle nested structures
            arg_pairs = []
            paren_count = 0
            bracket_count = 0
            brace_count = 0
            current_arg = ""

            for char in args_string:
                if char in "([{":
                    if char == "(":
                        paren_count += 1
                    elif char == "[":
                        bracket_count += 1
                    elif char == "{":
                        brace_count += 1
                elif char in ")]}":
                    if char == ")":
                        paren_count -= 1
                    elif char == "]":
                        bracket_count -= 1
                    elif char == "}":
                        brace_count -= 1
                elif (
                    char == ","
                    and paren_count == 0
                    and bracket_count == 0
                    and brace_count == 0
                ):
                    arg_pairs.append(current_arg.strip())
                    current_arg = ""
                    continue

                current_arg += char

            if current_arg.strip():
                arg_pairs.append(current_arg.strip())

            # Parse each argument pair
            for arg_pair in arg_pairs:
                if "=" in arg_pair:
                    key, value = arg_pair.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Try to evaluate the value safely
                    try:
                        # Handle string literals
                        if value.startswith("'") and value.endswith("'"):
                            args[key] = value[1:-1]
                        elif value.startswith('"') and value.endswith('"'):
                            args[key] = value[1:-1]
                        # Handle lists and dicts (for items parameter)
                        elif value.startswith("[") or value.startswith("{"):
                            args[key] = ast.literal_eval(value)
                        # Handle numbers
                        elif value.replace(".", "").replace("-", "").isdigit():
                            if "." in value:
                                args[key] = float(value)
                            else:
                                args[key] = int(value)
                        else:
                            # Default to string
                            args[key] = value
                    except (ValueError, SyntaxError):
                        # If evaluation fails, keep as string
                        args[key] = value

        return func_name, args

    @staticmethod
    def convert_legacy_args_to_tool_args(
        func_name: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert legacy run_actions.py argument format to tool argument format."""

        if func_name == "harvest_resource":
            return {
                "position": Position(args["x"], args["y"]),
                "quantity": args.get("quantity", 1),
            }

        elif func_name == "move_to":
            return {"position": Position(args["end_x"], args["end_y"])}

        elif func_name == "extract_item":
            # Parse the items JSON and get the first item
            items_str = args["items"].replace("'", '"')
            items_list = json.loads(items_str)
            if items_list:
                item_info = items_list[0]
                entity = ActionConverter._get_prototype(item_info["item"])

                return {
                    "entity": entity,
                    "source": Position(args["entity_x"], args["entity_y"]),
                    "quantity": item_info.get("count", 1),
                }

        elif func_name == "place_entity":
            # For place_entity, convert item to entity and create Position
            item_name = args["item"]
            entity = ActionConverter._get_prototype(item_name)

            result = {"entity": entity, "position": Position(args["x"], args["y"])}

            if "direction" in args:
                result["direction"] = Direction.from_int(int(args["direction"]))

            return result

        elif func_name == "craft_item":
            result = {}
            if "recipe" in args:
                result["entity"] = args["recipe"]
            if "count" in args:
                result["quantity"] = args["count"]
            return result

        elif func_name == "insert_item":
            # Parse the items JSON and get the first item
            items_str = args["items"].replace("'", '"')
            items_list = json.loads(items_str)
            if items_list:
                item_info = items_list[0]
                entity = ActionConverter._get_prototype(item_info["item"])

                return {
                    "entity": entity,
                    "target": Position(args["entity_x"], args["entity_y"]),
                    "quantity": item_info.get("count", 1),
                }

        elif func_name == "pickup_entity":
            entity_name = args["entity"]
            entity = ActionConverter._get_prototype(entity_name)

            return {"entity": entity, "position": Position(args["x"], args["y"])}

        elif func_name == "set_research":
            technology_name = args["technology"]

            try:
                if hasattr(technology_name, "value"):
                    technology = technology_name
                else:
                    technology = Technology(technology_name)
            except (ValueError, AttributeError):
                technology = technology_name

            return {"technology": technology}

        elif func_name == "set_entity_recipe":
            # Convert entity name and position to PlaceholderEntity, and recipe to RecipeName
            entity_name = args["entity"]
            recipe_name = args["new_recipe"]
            position = Position(args["x"], args["y"])

            # Create a placeholder entity at the given position
            entity = PlaceholderEntity(name=entity_name, position=position)

            # Convert recipe name to appropriate type - try Prototype first, then RecipeName
            from fle.env.game_types import RecipeName, Prototype

            prototype = None

            # First try to find it in Prototype enum (most recipes are here)
            try:
                for proto in Prototype:
                    if proto.value[0] == recipe_name:
                        prototype = proto
                        break
            except Exception:
                pass

            # If not found in Prototype, try RecipeName enum (for fluid recipes)
            if prototype is None:
                try:
                    prototype = RecipeName(recipe_name)
                except (ValueError, AttributeError):
                    # Fall back to string if neither enum works
                    prototype = recipe_name

            return {"entity": entity, "prototype": prototype}

        # Default: return args as-is
        return args

    @staticmethod
    def execute_tool_call_in_batch(
        namespace, func_name: str, args: Dict[str, Any], tick: int
    ) -> Any:
        """Execute a tool call with proper argument conversion."""
        if not hasattr(namespace, func_name):
            print(f"Warning: Function '{func_name}' not found in namespace")
            return None

        func = getattr(namespace, func_name)
        filtered_args = {
            k: v for k, v in args.items() if k not in ["start_tick", "end_tick", "tick"]
        }

        # Delegate to specific converters
        converter_map = {
            "move_to": ActionConverter._convert_move_to,
            "harvest_resource": ActionConverter._convert_harvest_resource,
            "place_entity": ActionConverter._convert_place_entity,
            "craft_item": ActionConverter._convert_craft_item,
            "insert_item": ActionConverter._convert_insert_item,
            "extract_item": ActionConverter._convert_extract_item,
            "pickup_entity": ActionConverter._convert_pickup_entity,
            "set_research": ActionConverter._convert_set_research,
            "inspect_inventory": ActionConverter._convert_inspect_inventory,
            "set_entity_recipe": ActionConverter._convert_set_entity_recipe,
        }

        converter = converter_map.get(func_name)
        if converter:
            return converter(func, filtered_args, tick)

        print(f"Warning: Unhandled function '{func_name}' with args {filtered_args}")
        return None

    @staticmethod
    def _convert_move_to(func, args: Dict[str, Any], tick: int):
        if "end_x" in args and "end_y" in args:
            return func(position=Position(args["end_x"], args["end_y"]), tick=tick)

    @staticmethod
    def _convert_harvest_resource(func, args: Dict[str, Any], tick: int):
        if "x" in args and "y" in args:
            return func(position=Position(args["x"], args["y"]), tick=tick)

    @staticmethod
    def _convert_place_entity(func, args: Dict[str, Any], tick: int):
        if "item" in args and "x" in args and "y" in args:
            entity = ActionConverter._get_prototype(args["item"])
            position = Position(args["x"], args["y"])
            kwargs = {"entity": entity, "position": position, "tick": tick}

            if "direction" in args:
                kwargs["direction"] = Direction.from_int(int(args["direction"]))

            return func(**kwargs)

    @staticmethod
    def _convert_craft_item(func, args: Dict[str, Any], tick: int):
        entity = args.get("recipe")
        quantity = args.get("count", 1)
        return func(entity=entity, quantity=quantity, tick=tick)

    @staticmethod
    def _convert_insert_item(func, args: Dict[str, Any], tick: int):
        if "items" in args and "entity_x" in args and "entity_y" in args:
            items_data = ActionConverter._parse_items_string(args["items"])
            if not items_data:
                return None

            item_info = items_data[0]  # For now, only handle the first item
            entity = ActionConverter._get_prototype(item_info["item"])
            quantity = item_info.get("count", 1)

            target_position = Position(args["entity_x"], args["entity_y"])
            target_entity_name = args.get("entity")

            target = (
                PlaceholderEntity(name=target_entity_name, position=target_position)
                if target_entity_name
                else target_position
            )

            return func(entity=entity, target=target, quantity=quantity, tick=tick)

    @staticmethod
    def _convert_extract_item(func, args: Dict[str, Any], tick: int):
        if "items" in args and "entity_x" in args and "entity_y" in args:
            items_data = ActionConverter._parse_items_string(args["items"])
            if not items_data:
                return None

            if len(items_data) > 1:
                print(
                    f"Warning: Extracting multiple items is not supported, missing: {items_data[1:]}"
                )

            item_info = items_data[0]  # For now, only handle the first item
            entity = ActionConverter._get_prototype(item_info["item"])
            quantity = item_info.get("count", 1)
            source_position = Position(args["entity_x"], args["entity_y"])

            return func(
                entity=entity, source=source_position, quantity=quantity, tick=tick
            )

    @staticmethod
    def _convert_pickup_entity(func, args: Dict[str, Any], tick: int):
        if "entity" in args and "x" in args and "y" in args:
            entity_name = args["entity"]
            # Skip if entity is blank or empty
            if not entity_name or not entity_name.strip():
                print(
                    f"Warning: Skipping pickup_entity with blank entity at tick {tick}"
                )
                return None

            entity = ActionConverter._get_prototype(entity_name)
            position = Position(args["x"], args["y"])
            return func(entity=entity, position=position, tick=tick)

    @staticmethod
    def _convert_set_research(func, args: Dict[str, Any], tick: int):
        technology_name = args.get("technology") or args.get("research")
        if technology_name:
            try:
                technology = (
                    technology_name
                    if hasattr(technology_name, "value")
                    else Technology(technology_name)
                )
            except (ValueError, AttributeError):
                print(
                    f"Warning: No Technology enum found for '{technology_name}', using string"
                )
                technology = technology_name
            return func(technology=technology, tick=tick)

    @staticmethod
    def _convert_inspect_inventory(func, args: Dict[str, Any], tick: int):
        return func(tick=tick)

    @staticmethod
    def _convert_set_entity_recipe(func, args: Dict[str, Any], tick: int):
        entity_name = args.get("entity")
        recipe_name = args.get("new_recipe")
        x = args.get("x")
        y = args.get("y")

        if entity_name and recipe_name and x is not None and y is not None:
            position = Position(x, y)

            # Create a placeholder entity at the given position
            entity = PlaceholderEntity(name=entity_name, position=position)

            # Convert recipe name to appropriate type - try Prototype first, then RecipeName
            from fle.env.game_types import RecipeName, Prototype

            prototype = None

            # First try to find it in Prototype enum (most recipes are here)
            try:
                for proto in Prototype:
                    if proto.value[0] == recipe_name:
                        prototype = proto
                        break
            except Exception:
                pass

            # If not found in Prototype, try RecipeName enum (for fluid recipes)
            if prototype is None:
                try:
                    prototype = RecipeName(recipe_name)
                except (ValueError, AttributeError):
                    # Fall back to string if neither enum works
                    prototype = recipe_name

            return func(entity=entity, prototype=prototype, tick=tick)

    @staticmethod
    def _get_prototype(item_name: str):
        """Convert item name to Prototype enum instance."""
        if item_name in prototype_by_name:
            return prototype_by_name[item_name]
        else:
            print(f"Warning: No Prototype found for '{item_name}', using string")
            return item_name

    @staticmethod
    def _parse_items_string(items_str: str) -> List[Dict]:
        """Parse items string to list of item dictionaries."""
        if not items_str or not items_str.strip():
            return []

        try:
            items_str = items_str.replace("'", '"')
            return json.loads(items_str)
        except json.JSONDecodeError:
            return []
