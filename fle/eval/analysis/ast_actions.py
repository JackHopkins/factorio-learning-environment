"""
AST-based action parsing for Factorio programs.

This module provides robust parsing of Factorio action calls using Python's AST
module, supporting move_to, place_entity, place_entity_next_to, connect_entities,
and insert_item actions.

STATELESS EXTRACTOR: This module only extracts and normalizes actions. It does NOT
decide camera shots or emit any cinema code. All shot decisions are made by the
Cinematographer module.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class ActionSite:
    """Represents a detected action call in the code.

    This is the canonical representation of a Factorio action extracted from AST.
    All field names are normalized to snake_case for consistency.
    """

    type: str  # Action type: move_to, place_entity, etc.
    args: dict[str, Any]  # Parsed arguments specific to action type
    line_no: int  # Line number where action was found
    col_offset: int  # Column offset for precise location
    end_line_no: Optional[int] = None  # End line for multi-line calls
    end_col_offset: Optional[int] = None  # End column for multi-line calls
    program_id: Optional[str] = None  # Optional program identifier for ordering
    created_at: Optional[float] = None  # Optional timestamp for ordering

    @property
    def kind(self) -> str:
        """Alias for type to match the expected interface."""
        return self.type

    @property
    def line_span(self) -> tuple[int, int]:
        """Return (start_line, end_line) tuple for line span."""
        return (self.line_no, self.end_line_no or self.line_no)

    def to_action_event(self) -> dict[str, Any]:
        """Convert to normalized ActionEvent for Cinematographer consumption."""
        return {
            "type": self.type,
            "args": self.args,
            "line_span": self.line_span,
            "program_id": self.program_id,
            "created_at": self.created_at,
        }


def parse_actions(
    code: str, program_id: Optional[str] = None, created_at: Optional[float] = None
) -> List[ActionSite]:
    """
    Parse Factorio actions from Python code using AST.

    Args:
        code: Python code string to parse
        program_id: Optional program identifier for ordering
        created_at: Optional timestamp for ordering

    Returns:
        List of ActionSite objects representing detected actions
    """
    try:
        tree = ast.parse(code)
        visitor = ActionVisitor()
        visitor.visit(tree)

        # Add metadata to all actions
        for action in visitor.actions:
            action.program_id = program_id
            action.created_at = created_at

        return visitor.actions
    except SyntaxError:
        # If code has syntax errors, return empty list
        return []


def normalize_prototype_name(prototype: str) -> str:
    """Normalize prototype names to snake_case for consistency.

    Args:
        prototype: Raw prototype name from code

    Returns:
        Normalized snake_case prototype name
    """
    if not prototype:
        return prototype

    # Handle common variations
    normalized = prototype.lower()

    # Handle specific known variations
    variations = {
        "steamengine": "steam_engine",
        "burnerminingdrill": "burner_mining_drill",
        "electricminingdrill": "electric_mining_drill",
        "stonefurnace": "stone_furnace",
        "steelfurnace": "steel_furnace",
        "electricfurnace": "electric_furnace",
        "assemblymachine1": "assembly_machine_1",
        "assemblymachine2": "assembly_machine_2",
        "assemblymachine3": "assembly_machine_3",
        "offshorepump": "offshore_pump",
    }

    return variations.get(normalized, normalized)


def create_action_stream(actions: List[ActionSite]) -> List[dict[str, Any]]:
    """Create a normalized ActionStream from ActionSite objects.

    This is the canonical data contract for action data flowing to Cinematographer.

    Args:
        actions: List of ActionSite objects

    Returns:
        List of normalized action event dictionaries
    """
    return [action.to_action_event() for action in actions]


class ActionVisitor(ast.NodeVisitor):
    """AST visitor that detects Factorio action calls."""

    def __init__(self):
        self.actions: List[ActionSite] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect action patterns."""
        if not isinstance(node.func, ast.Name):
            # Handle method calls like obj.method()
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            else:
                self.generic_visit(node)
                return
        else:
            func_name = node.func.id

        # Check if this is a known action
        if func_name == "move_to":
            self._parse_move_to(node)
        elif func_name == "place_entity":
            self._parse_place_entity(node)
        elif func_name == "place_entity_next_to":
            self._parse_place_entity_next_to(node)
        elif func_name == "connect_entities":
            self._parse_connect_entities(node)
        elif func_name == "insert_item":
            self._parse_insert_item(node)

        # Continue visiting other nodes
        self.generic_visit(node)

    def _parse_move_to(self, node: ast.Call) -> None:
        """Parse move_to(destination) calls."""
        if not node.args:
            return

        # Get the destination argument (first positional arg)
        dest_arg = node.args[0]
        dest_expr = self._stringify_expression(dest_arg)

        # Extract keyword arguments
        kwargs = self._extract_keywords(node)

        action = ActionSite(
            type="move_to",
            args={"destination": dest_expr, "pos_src": dest_expr, **kwargs},
            line_no=node.lineno,
            col_offset=node.col_offset,
            end_line_no=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
        self.actions.append(action)

    def _parse_place_entity(self, node: ast.Call) -> None:
        """Parse place_entity(prototype, position, **kwargs) calls."""
        if not node.args:
            return

        # Get the prototype argument (first positional arg)
        prototype_arg = node.args[0]
        prototype_name = self._extract_prototype_name(prototype_arg)

        # Get the position argument (second positional arg, if present)
        position_expr = None
        if len(node.args) >= 2:
            position_expr = self._stringify_expression(node.args[1])

        # Extract keyword arguments
        kwargs = self._extract_keywords(node)

        # Build args dict
        args = {"prototype": prototype_name, **kwargs}
        if position_expr:
            args["position"] = position_expr

        action = ActionSite(
            type="place_entity",
            args=args,
            line_no=node.lineno,
            col_offset=node.col_offset,
            end_line_no=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
        self.actions.append(action)

    def _parse_place_entity_next_to(self, node: ast.Call) -> None:
        """Parse place_entity_next_to(prototype, target, position, **kwargs) calls."""
        if len(node.args) < 2:
            return

        # Get prototype and target arguments
        prototype_arg = node.args[0]
        target_arg = node.args[1]

        prototype_name = self._extract_prototype_name(prototype_arg)
        target_expr = self._stringify_expression(target_arg)

        # Get the position argument (third positional arg, if present)
        position_expr = None
        if len(node.args) >= 3:
            position_expr = self._stringify_expression(node.args[2])

        # Extract keyword arguments
        kwargs = self._extract_keywords(node)

        # Build args dict
        args = {"prototype": prototype_name, "target": target_expr, **kwargs}
        if position_expr:
            args["position"] = position_expr

        action = ActionSite(
            type="place_entity_next_to",
            args=args,
            line_no=node.lineno,
            col_offset=node.col_offset,
            end_line_no=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
        self.actions.append(action)

    def _parse_connect_entities(self, node: ast.Call) -> None:
        """Parse connect_entities(entity_a, entity_b, prototype) calls."""
        if len(node.args) < 3:
            return

        # Get the three arguments
        entity_a_arg = node.args[0]
        entity_b_arg = node.args[1]
        prototype_arg = node.args[2]

        a_expr = self._stringify_expression(entity_a_arg)
        b_expr = self._stringify_expression(entity_b_arg)
        proto_name = self._extract_prototype_name(prototype_arg)

        # Extract keyword arguments
        kwargs = self._extract_keywords(node)

        action = ActionSite(
            type="connect_entities",
            args={
                "a_expr": a_expr,
                "b_expr": b_expr,
                "proto_name": proto_name,
                "a_src": a_expr,
                "b_src": b_expr,
                **kwargs,
            },
            line_no=node.lineno,
            col_offset=node.col_offset,
            end_line_no=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
        self.actions.append(action)

    def _parse_insert_item(self, node: ast.Call) -> None:
        """Parse insert_item(prototype, position, **kwargs) calls."""
        if not node.args:
            return

        # Get the prototype argument (first positional arg)
        prototype_arg = node.args[0]
        prototype_name = self._extract_prototype_name(prototype_arg)

        # Get the position argument (second positional arg, if present)
        position_expr = None
        if len(node.args) >= 2:
            position_expr = self._stringify_expression(node.args[1])

        # Extract keyword arguments
        kwargs = self._extract_keywords(node)

        # Build args dict
        args = {"prototype": prototype_name, **kwargs}
        if position_expr:
            args["position"] = position_expr

        action = ActionSite(
            type="insert_item",
            args=args,
            line_no=node.lineno,
            col_offset=node.col_offset,
            end_line_no=node.end_lineno,
            end_col_offset=node.end_col_offset,
        )
        self.actions.append(action)

    def _stringify_expression(self, node: ast.AST) -> str:
        """Convert an AST node back to a string representation."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._stringify_expression(node.value)
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.Call):
            func = self._stringify_expression(node.func)
            args = [self._stringify_expression(arg) for arg in node.args]
            kwargs = []
            for keyword in node.keywords:
                if keyword.arg:
                    kwargs.append(
                        f"{keyword.arg}={self._stringify_expression(keyword.value)}"
                    )
                else:  # **kwargs
                    kwargs.append(f"**{self._stringify_expression(keyword.value)}")

            all_args = args + kwargs
            return f"{func}({', '.join(all_args)})"
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return f'"{node.value}"'
            else:
                return repr(node.value)
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return repr(node.n)
        elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
            return repr(node.s)
        elif isinstance(node, ast.UnaryOp):
            # Handle negative numbers like -0.5
            if isinstance(node.op, ast.USub):
                operand = self._stringify_expression(node.operand)
                return f"-{operand}"
            else:
                return f"<{type(node.op).__name__}>{self._stringify_expression(node.operand)}"
        elif isinstance(node, ast.List):
            elements = [self._stringify_expression(el) for el in node.elts]
            return f"[{', '.join(elements)}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._stringify_expression(el) for el in node.elts]
            return f"({', '.join(elements)})"
        elif isinstance(node, ast.Dict):
            pairs = []
            for key, value in zip(node.keys, node.values):
                key_str = self._stringify_expression(key) if key else "None"
                value_str = self._stringify_expression(value)
                pairs.append(f"{key_str}: {value_str}")
            return f"{{{', '.join(pairs)}}}"
        else:
            # For complex expressions, return a simplified representation
            return f"<{type(node).__name__}>"

    def _extract_prototype_name(self, node: ast.AST) -> str:
        """Extract prototype name from Prototype.Name or similar patterns."""
        raw_name = ""
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "Prototype":
                raw_name = node.attr
            else:
                # Handle nested attributes like obj.Prototype.Name
                raw_name = self._stringify_expression(node)
        elif isinstance(node, ast.Name):
            raw_name = node.id
        else:
            raw_name = self._stringify_expression(node)

        # Normalize the prototype name
        return normalize_prototype_name(raw_name)

    def _extract_keywords(self, node: ast.Call) -> dict[str, Any]:
        """Extract keyword arguments from a function call."""
        kwargs = {}
        for keyword in node.keywords:
            if keyword.arg:  # Skip **kwargs
                kwargs[keyword.arg] = self._stringify_expression(keyword.value)
        return kwargs
