import os
import importlib.util
import inspect
from typing import Any, List, Tuple, Optional

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

def load_schema(folder_path: str) -> str:

    schema = ""
    """Main function to extract and output the required information."""
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
                        named_call_signature_string = f'{file[:-3]}{localed_call_signature_string}\n"""\n{docstring}\n"""\n\n'

                        schema += named_call_signature_string
    return schema

def load_definitions(file_path: str) -> str:
    with open(file_path, 'r') as file:
        return file.read()



if __name__ == "__main__":
    # get execution path
    execution_path = os.path.dirname(os.path.realpath(__file__))

    folder_path = f'{execution_path}/../controllers'  # path to the 'controller' folder
    load_schema(folder_path)
