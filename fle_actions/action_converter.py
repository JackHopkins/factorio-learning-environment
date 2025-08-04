"""
Handles conversion between different action argument formats.
"""

import json
from typing import Dict, Any, List

from fle.env.entities import Position, Direction, PlaceholderEntity
from fle.env.game_types import prototype_by_name, Technology


class ActionConverter:
    """Handles conversion between different action argument formats."""

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
            entity = ActionConverter._get_prototype(args["entity"])
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
