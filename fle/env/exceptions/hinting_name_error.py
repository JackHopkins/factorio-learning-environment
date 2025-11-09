from typing import Any, get_type_hints
import inspect


class HintingNameError(NameError):
    def __init__(self, original_error: str, suggestions: list[tuple[str, str]]):
        self.suggestions = suggestions
        message = original_error
        if suggestions:
            suggestion_strs = [
                f"{name}: {type_hint}" if type_hint else name
                for name, type_hint in suggestions
            ]
            message += "\nDid you mean one of these?\n  " + "\n  ".join(suggestion_strs)
        super().__init__(message)


def get_value_type_str(value: Any) -> str:
    """Get a string representation of a value's type, including annotations if available."""
    if value is None:
        return "None"

    # Handle functions specially to show their signature
    if inspect.isfunction(value):
        try:
            sig = inspect.signature(value)
            type_hints = get_type_hints(value)

            # Format parameters with their type hints
            params = []
            for name, param in sig.parameters.items():
                param_type = type_hints.get(name, Any).__name__
                params.append(f"{name}: {param_type}")

            # Get return type
            return_type = type_hints.get("return", Any).__name__

            return f"def ({', '.join(params)}) -> {return_type}"
        except Exception as e:
            # Provide more helpful fallback information for functions
            try:
                # Try to get at least the function signature without type hints
                sig = inspect.signature(value)
                param_names = [param for param in sig.parameters.keys()]
                func_name = getattr(value, '__name__', 'function')
                if param_names:
                    return f"function {func_name}({', '.join(param_names)})"
                else:
                    return f"function {func_name}()"
            except Exception:
                # Last resort fallback with function name if available
                func_name = getattr(value, '__name__', 'unknown')
                return f"function {func_name} (signature unavailable)"

    # Handle class instances
    if hasattr(value, "__class__"):
        # For built-in types, just use the class name
        if value.__class__.__module__ == "builtins":
            return value.__class__.__name__
        # For custom classes, include the module name
        return f"{value.__class__.__module__}.{value.__class__.__name__}"

    # Improved fallback with more context
    try:
        type_name = type(value).__name__
        # Try to get the module to provide more context
        if hasattr(type(value), '__module__') and type(value).__module__ not in ('builtins', '__main__'):
            return f"{type(value).__module__}.{type_name}"
        return type_name
    except Exception:
        # Absolute last resort - provide as much info as possible
        return f"<object of unknown type: {repr(value)[:50]}>" if hasattr(value, '__repr__') else "<object of unknown type>"
