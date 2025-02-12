import marshal
import types


class SerializableFunction:
    """Wrapper to make function objects serializable and callable"""

    def __init__(self, func, instance=None):
        self.code_bytes = marshal.dumps(func.__code__)
        self.name = func.__name__
        self.defaults = func.__defaults__
        self.closure = None
        # These won't be pickled
        self._instance = instance
        self._cached_func = None

    def __getstate__(self):
        """Control which attributes are pickled"""
        return {
            'code_bytes': self.code_bytes,
            'name': self.name,
            'defaults': self.defaults,
            'closure': self.closure
        }

    def __setstate__(self, state):
        """Restore state after unpickling"""
        self.code_bytes = state['code_bytes']
        self.name = state['name']
        self.defaults = state['defaults']
        self.closure = state['closure']
        self._instance = None
        self._cached_func = None

    def bind(self, instance):
        """Bind this function to an instance after unpickling"""
        self._instance = instance
        self._cached_func = None
        return self

    def __call__(self, *args, **kwargs):
        """Make the serialized function directly callable"""
        if self._cached_func is None:
            if self._instance is None:
                raise RuntimeError("Function must be bound to an instance before calling")
            self._cached_func = self.reconstruct(self._instance, self)
        return self._cached_func(*args, **kwargs)

    @staticmethod
    def reconstruct(instance, func_data):
        """Reconstruct a function with proper globals from the instance"""
        globals_dict = {}
        # Add instance attributes
        for name in dir(instance):
            if not name.startswith('_'):
                globals_dict[name] = getattr(instance, name)
        # Add builtins
        for name in dir(builtins):
            if not name.startswith('_'):
                globals_dict[name] = getattr(builtins, name)

        code = marshal.loads(func_data.code_bytes)

        new_func = types.FunctionType(
            code,
            globals_dict,
            func_data.name,
            func_data.defaults,
            func_data.closure
        )
        return new_func
