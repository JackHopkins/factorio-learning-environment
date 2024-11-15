import os
import importlib.util
import inspect
from typing import Any, List, Tuple, Optional
import ast

def load_module_from_path(path: str) -> Optional[Any]:
    """Load and return a module from the given path."""
    spec = importlib.util.spec_from_file_location("temp_module", path)
    if not spec:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def extract_call_info(cls: Any) -> Tuple[str, str, str]:
    """Extract input types, output type hints, and docstring of the __call__ method."""
    if not hasattr(cls, '__call__'):
        return "", "", ""

    call_signature = inspect.signature(cls.__call__)
    call_signature_string = str(call_signature)
    input_types = ", ".join(str(param.annotation) for _, param in call_signature.parameters.items())
    output_type = str(call_signature.return_annotation)

    docstring = inspect.getdoc(cls.__call__)
    return input_types, output_type, docstring, call_signature_string

def load_controller_names(folder_path: str) -> List[str]:
    names = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py") and file[0] != "_":
                full_path = os.path.join(root, file)
                module = load_module_from_path(full_path)
                if not module:
                    continue
                names.append(file[:-3])
    return names
def load_schema(folder_path: str, with_docstring=True) -> str:

    schema = ""

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                module = load_module_from_path(full_path)
                if not module:
                    continue

                # Iterate through all classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):

                    if name == "ObserveAll" or name == "ClearEntities":
                        continue

                    # Check if the class is defined in this module (and not imported from elsewhere)
                    if obj.__module__ == module.__name__:
                        input_types, output_type, docstring, call_signature_string = extract_call_info(obj)
                        if not all([input_types, output_type, docstring]):
                            continue
                        if file[0] == "_":
                            continue

                        localed_call_signature_string = call_signature_string \
                            .replace("self, ", "") \
                            .replace("factorio_entities.", "") \
                            .replace("factorio_instance.", "") \
                            .replace("factorio_types.", "")

                        docstring_element = f'"""\n{docstring}\n"""\n\n' if with_docstring else ""
                        named_call_signature_string = f'{file[:-3]}{localed_call_signature_string}\n{docstring_element}'

                        schema += named_call_signature_string
    return schema

def load_definitions(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()


import ast
from typing import List


class CodeStructureVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_indent = 0
        self.lines = []

    def visit_ClassDef(self, node):
        # Build class definition string
        bases = [ast.unparse(base) for base in node.bases]
        class_def = f"{'    ' * self.current_indent}class {node.name}"
        if bases:
            class_def += f"({', '.join(bases)})"
        class_def += ":"
        self.lines.append(class_def)

        # Increase indent for class contents
        self.current_indent += 1

        # Process class body
        for item in node.body:
            if isinstance(item, ast.ClassDef):
                # Handle nested classes
                self.visit_ClassDef(item)
            elif isinstance(item, ast.FunctionDef):
                # Handle method definitions
                self.visit_FunctionDef(item)
            elif isinstance(item, ast.AnnAssign):
                # Handle annotated assignments (type hints)
                target = ast.unparse(item.target)
                annotation = ast.unparse(item.annotation)
                self.lines.append(f"{'    ' * self.current_indent}{target}: {annotation}")
            elif isinstance(item, ast.Assign):
                # Handle regular assignments
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        value = ast.unparse(item.value)
                        self.lines.append(f"{'    ' * self.current_indent}{target.id} = {value}")

        # Decrease indent after processing class contents
        self.current_indent -= 1

    def visit_FunctionDef(self, node):
        # Build function signature
        args = []
        for arg in node.args.args:
            if hasattr(arg, 'annotation') and arg.annotation:
                args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
            else:
                args.append(arg.arg)

        # Handle return annotation
        returns = ""
        if node.returns:
            returns = f" -> {ast.unparse(node.returns)}"

        signature = f"{'    ' * self.current_indent}def {node.name}({', '.join(args)}){returns}:"
        self.lines.append(signature)


def extract_class_structure(code: str) -> str:
    """
    Extracts class definitions, type annotations, and method signatures from Python code.

    Args:
        code (str): Python source code as a string

    Returns:
        str: Formatted string containing class structures and method signatures
    """
    try:
        tree = ast.parse(code)
        visitor = CodeStructureVisitor()
        visitor.visit(tree)
        return "\n".join(visitor.lines)
    except SyntaxError:
        return "Error: Invalid Python syntax in the input code"


def parse_file_for_structure(file_path: str) -> str:
    """
    Reads a Python file and extracts all class structures and method signatures.

    Args:
        file_path (str): Path to the Python file

    Returns:
        str: Formatted string containing class structures and method signatures
    """
    with open(file_path, 'r') as file:
        code = file.read()
    return extract_class_structure(code)

if __name__ == "__main__":
    # get execution path
    execution_path = os.path.dirname(os.path.realpath(__file__))

    folder_path = f'{execution_path}/../controllers'  # path to the 'controller' folder
    load_schema(folder_path)
