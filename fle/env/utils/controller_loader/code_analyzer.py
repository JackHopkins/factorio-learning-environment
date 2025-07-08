import ast
import inspect
from typing import Any

from fle.env.utils.controller_loader.call_info import CallInfo


class CodeAnalyzer:
    """Analyzes Python code for class and method structures."""

    @staticmethod
    def extract_class_structure(code: str) -> str:
        """
        Extracts class definitions, type annotations, and method signatures from Python code.

        Args:
            code (str): Python source code to analyze

        Returns:
            str: Formatted string containing class structures and method signatures
        """

        class _StructureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_indent = 0
                self.lines = []

            def _get_docstring(self, node) -> str | None:
                """Extract docstring from a node if present."""
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Str)
                ):
                    return node.body[0].value.s
                return None

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                # Build class definition with inheritance
                bases = [ast.unparse(base) for base in node.bases]
                class_def = f"{'    ' * self.current_indent}class {node.name}"
                if bases:
                    class_def += f"({', '.join(bases)})"
                class_def += ":"
                self.lines.append(class_def)

                # Process class body with increased indentation
                self.current_indent += 1

                # Add class docstring if present
                docstring = self._get_docstring(node)
                if docstring:
                    # Format multi-line docstrings properly
                    formatted_docstring = '"""'
                    if "\n" in docstring:
                        formatted_docstring += "\n" + ("    " * self.current_indent)
                        formatted_docstring += docstring.strip() + "\n"
                        formatted_docstring += "    " * self.current_indent
                    else:
                        formatted_docstring += docstring
                    formatted_docstring += '"""'
                    self.lines.append(
                        f"{'    ' * self.current_indent}{formatted_docstring}"
                    )

                for item in node.body:
                    self.visit(item)
                self.current_indent -= 1

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                # Build function arguments with type annotations
                args = []
                for arg in node.args.args:
                    if hasattr(arg, "annotation") and arg.annotation:
                        args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                    else:
                        args.append(arg.arg)

                # Add return type annotation if present
                returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""

                # Construct full function signature
                signature = f"{'    ' * self.current_indent}def {node.name}({', '.join(args)}){returns}:"
                self.lines.append(signature)

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                # Handle annotated assignments (type hints)
                target = ast.unparse(node.target)
                annotation = ast.unparse(node.annotation)
                self.lines.append(
                    f"{'    ' * self.current_indent}{target}: {annotation}"
                )

            def visit_Assign(self, node: ast.Assign) -> None:
                # Handle regular assignments
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        value = ast.unparse(node.value)
                        self.lines.append(
                            f"{'    ' * self.current_indent}{target.id} = {value}"
                        )

        try:
            tree = ast.parse(code)
            visitor = _StructureVisitor()
            visitor.visit(tree)
            return "\n".join(visitor.lines)
        except SyntaxError as e:
            return f"Error: Invalid Python syntax - {str(e)}"

    @staticmethod
    def parse_file_for_structure(file_path: str) -> str:
        """
        Reads a Python file and extracts class structures and method signatures.

        Args:
            file_path (str): Path to the Python file to analyze

        Returns:
            str: Formatted string containing class structures and method signatures
        """
        try:
            with open(file_path, "r") as file:
                code = file.read()
            return CodeAnalyzer.extract_class_structure(code)
        except FileNotFoundError:
            return f"Error: File not found - {file_path}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

    @staticmethod
    def extract_call_info(cls: Any) -> CallInfo:
        """Extract information about a class's __call__ method."""
        if not hasattr(cls, "__call__"):
            return CallInfo("", "", "", "")

        call_signature = inspect.signature(cls.__call__)
        input_types = ", ".join(
            str(param.annotation) for _, param in call_signature.parameters.items()
        )
        output_type = str(call_signature.return_annotation)
        docstring = inspect.getdoc(cls.__call__) or ""

        return CallInfo(
            input_types=input_types,
            output_type=output_type,
            docstring=docstring,
            signature=str(call_signature),
        )
