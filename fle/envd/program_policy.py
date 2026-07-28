"""Static guardrails for Python programs submitted through ``factorio-envd``.

FLE's native REPL is intentionally powerful and exposes normal Python imports
and several namespace internals. That is useful for trusted research scripts,
but it is too much authority for model-generated programs received over HTTP.
This module provides a conservative action-profile guard. It is defense in
depth, not a replacement for OS/container isolation in production.
"""

from __future__ import annotations

import ast

from fle.envd.errors import EnvironmentServiceError


class ProgramPolicyViolation(EnvironmentServiceError):
    """The submitted program exceeds the public ``fle-program-v1`` profile."""


MAX_PROGRAM_BYTES = 32_768
MAX_AST_NODES = 2_000
ALLOWED_IMPORT_ROOTS = {
    "collections",
    "functools",
    "itertools",
    "math",
    "statistics",
}
FORBIDDEN_NAMES = {
    "__builtins__",
    "breakpoint",
    "classmethod",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "exit",
    "getattr",
    "globals",
    "help",
    "input",
    "instance",
    "locals",
    "memoryview",
    "nonlocal",
    "object",
    "open",
    "persistent_vars",
    "property",
    "quit",
    "setattr",
    "staticmethod",
    "super",
    "tcp_port",
    "type",
    "vars",
}
FORBIDDEN_NODE_TYPES = (
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Nonlocal,
)


def validate_program(code: str) -> None:
    """Reject host access, reflection, and pathological program structure."""

    if len(code.encode("utf-8")) > MAX_PROGRAM_BYTES:
        raise ProgramPolicyViolation(
            f"program exceeds the {MAX_PROGRAM_BYTES}-byte action-profile limit"
        )
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise ProgramPolicyViolation(f"program is not valid Python: {exc.msg}") from exc

    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise ProgramPolicyViolation(
            f"program exceeds the {MAX_AST_NODES}-node action-profile limit"
        )

    for node in nodes:
        if isinstance(node, FORBIDDEN_NODE_TYPES):
            raise ProgramPolicyViolation(
                f"{type(node).__name__} is not available in fle-program-v1"
            )
        if isinstance(node, ast.Name) and (
            node.id in FORBIDDEN_NAMES or node.id.startswith("_")
        ):
            raise ProgramPolicyViolation(
                f"name {node.id!r} is not available in fle-program-v1"
            )
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ProgramPolicyViolation(
                f"private attribute {node.attr!r} is not available in fle-program-v1"
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "__" in node.value:
                raise ProgramPolicyViolation(
                    "dunder attribute names are not available in fle-program-v1"
                )
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            roots = {module.split(".", 1)[0] for module in modules}
            unsupported = roots - ALLOWED_IMPORT_ROOTS
            if unsupported or (isinstance(node, ast.ImportFrom) and node.level):
                names = ", ".join(sorted(unsupported or roots))
                raise ProgramPolicyViolation(
                    f"imports are restricted by fle-program-v1; rejected: {names}"
                )
