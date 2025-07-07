import builtins
import inspect
import marshal
import types


class SerializableFunction:
    """Wrapper to make function objects serializable and callable with signature information"""

    def __init__(self, func, instance=None):
        """Initialize with a function"""
        self.code_bytes = marshal.dumps(func.__code__)
        self.name = func.__name__
        self.defaults = func.__defaults__
        self.closure = None
        self.docstring = func.__doc__

        # Store signature information including annotations
        try:
            sig = inspect.signature(func)
            # Get annotations directly from the function
            annotations = getattr(func, "__annotations__", {})

            # Store parameters with their annotations
            self.parameters = []
            for name, param in sig.parameters.items():
                annotation = annotations["args"].get(name, None)
                annotation_str = None
                if annotation:
                    annotation_str = getattr(annotation, "__name__", str(annotation))
                self.parameters.append((name, str(param), annotation_str))

            # Store return annotation
            self.return_annotation = annotations["args"].get("return", None)
            if self.return_annotation:
                self.return_annotation = getattr(
                    self.return_annotation, "__name__", str(self.return_annotation)
                )

        except (ValueError, TypeError):
            self.parameters = []
            self.return_annotation = None

        # These won't be pickled
        self._instance = instance
        self._cached_func = None

    def __getstate__(self):
        """Control which attributes are pickled"""
        return {
            "code_bytes": self.code_bytes,
            "name": self.name,
            "defaults": self.defaults,
            "closure": self.closure,
            "docstring": self.docstring,
            "parameters": self.parameters,
            "return_annotation": self.return_annotation,
        }

    def __setstate__(self, state):
        """Restore state after unpickling"""
        self.code_bytes = state["code_bytes"]
        self.name = state["name"]
        self.defaults = state["defaults"]
        self.closure = state["closure"]
        if "docstring" in state:
            self.docstring = state["docstring"]
        if "parameters" in state:
            self.parameters = state["parameters"]
        if "return_annotation" in state:
            self.return_annotation = state["return_annotation"]
        self._instance = None
        self._cached_func = None

    def __str__(self):
        """Return a string representation with function signature and docstring"""
        # Build parameter list preserving type annotations
        param_strs = []
        for name, param_str, annotation in self.parameters:
            if annotation:
                # Handle default values
                if "=" in param_str:
                    param_name, default = param_str.split("=", 1)
                    param_strs.append(f"{name}: {annotation}={default.strip()}")
                else:
                    param_strs.append(f"{name}: {annotation}")
            else:
                # No type annotation, use original parameter string
                param_strs.append(param_str)

        # Combine into function signature
        signature = f"({', '.join(param_strs)})"
        result = f"def {self.name}{signature}"

        # Add return annotation if it exists
        if self.return_annotation:
            result += f" -> {self.return_annotation}"

        # Add docstring if it exists
        if self.docstring:
            result += f'\n"""{self.docstring}"""'

        return result

    def bind(self, instance):
        """Bind this function to an instance after unpickling"""
        self._instance = instance
        self._cached_func = None
        return self

    def __call__(self, *args, **kwargs):
        """Make the serialized function directly callable"""
        if self._cached_func is None:
            if self._instance is None:
                raise RuntimeError(
                    "Function must be bound to an instance before calling"
                )
            self._cached_func = self.reconstruct(self._instance, self)
        return self._cached_func(*args, **kwargs)

    @staticmethod
    def reconstruct(instance, func_data):
        """Reconstruct a function with proper globals from the instance"""
        globals_dict = {}

        # Add instance attributes
        for name in dir(instance):
            if not name.startswith("_"):
                globals_dict[name] = getattr(instance, name)

        # Add builtins
        for name in dir(builtins):
            if not name.startswith("_"):
                globals_dict[name] = getattr(builtins, name)

        code = marshal.loads(func_data.code_bytes)

        new_func = types.FunctionType(
            code, globals_dict, func_data.name, func_data.defaults, func_data.closure
        )
        return new_func
