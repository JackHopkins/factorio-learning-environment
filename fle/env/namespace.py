import ast
import builtins
import inspect
import math
import pickle
import sys
import traceback
import types
from difflib import get_close_matches
from typing import Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel

from fle.commons.models.serializable_function import SerializableFunction
from fle.env import entities as ent

from fle.env.entities import Entity
from fle.env.exceptions.hinting_name_error import get_value_type_str
from fle.env.game_types import (
    Prototype,
    RecipeName,
    Resource,
    Technology,
    prototype_by_name,
)


class LoopContext:
    def __init__(self):
        self.in_loop = False
        self.loop_stack = []  # Stack to track nested loops
        self.state = "NORMAL"  # Can be "NORMAL", "BREAK", or "CONTINUE"

    def enter_loop(self, loop_node):
        self.in_loop = True
        self.loop_stack.append(loop_node)

    def exit_loop(self):
        if self.loop_stack:
            self.loop_stack.pop()
        self.in_loop = bool(self.loop_stack)
        self.state = "NORMAL"

    def handle_break(self):
        if not self.in_loop:
            raise SyntaxError("'break' outside loop")
        self.state = "BREAK"
        return False

    def handle_continue(self):
        if not self.in_loop:
            raise SyntaxError("'continue' outside loop")
        self.state = "CONTINUE"
        return False


class FactorioNamespace:
    def __init__(self, instance, agent_index):
        self.logging_results = {}
        self.line_value = 0
        self.persistent_vars = {}
        self.instance = instance
        self.tcp_port = instance.tcp_port
        self.max_sequential_exception_count = 1
        self._sequential_exception_count = 0
        self.log_counter = 0
        self.player_location = ent.Position(x=0, y=0)
        self.agent_index = agent_index
        self.agent_id = str(agent_index)
        self.loop_context = LoopContext()

        # Add all builtins to the namespace
        for name in dir(builtins):
            if not name.startswith("_"):  # Skip private/special names
                try:
                    setattr(self, name, getattr(builtins, name))
                    self.persistent_vars[name] = getattr(builtins, name)
                except Exception as e:
                    print(f"Failed to add builtin {name}: {e}")

        # Define assert function
        def assert_(expr, msg=None):
            if not expr:
                raise AssertionError(msg)

        # Add specific builtins that we definitely want to expose to the agent
        self.essential_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "int": int,
            "str": str,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "sum": sum,
            "min": min,
            "max": max,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "any": any,
            "all": all,
            "sorted": sorted,
            "reversed": reversed,
            "round": round,
            "abs": abs,
            "isinstance": isinstance,
            "type": type,
            "assert": assert_,
        }

        for name, func in self.essential_builtins.items():
            setattr(self, name, func)
            self.persistent_vars[name] = func

        # Turn this on to capture the outputs of all statements, rather than just `print` statement logs.
        self.capture_whole_output = False

        # We capture prints in order of them being run
        self.execution_trace = True

        # Available objects that the agent can interact with
        self.Prototype = Prototype
        self.Resource = Resource
        self.Direction = ent.Direction
        self.Position = ent.Position
        self.EntityStatus = ent.EntityStatus
        self.BoundingBox = ent.BoundingBox
        self.BuildingBox = ent.BuildingBox
        self.BeltGroup = ent.BeltGroup
        self.Technology = Technology
        self.Recipe = ent.Recipe
        self.PipeGroup = ent.PipeGroup
        self.ElectricityGroup = ent.ElectricityGroup
        self.BeltGroup = ent.BeltGroup
        self.Pipe = ent.Pipe
        self.RecipeName = RecipeName

        # TODO - We need to add all entity objects to the namespace, e.g 'Chest'

        self.prototype_by_name = prototype_by_name
        for name, value in self.prototype_by_name.items():
            if value.entity_class:
                setattr(self, value.name, value.entity_class)

        # Statically named directions
        self.UP, self.ABOVE, self.TOP = [ent.Direction.UP] * 3
        self.RIGHT, self.EAST = [ent.Direction.RIGHT] * 2
        self.LEFT, self.WEST = [ent.Direction.LEFT] * 2
        self.DOWN, self.BELOW, self.BOTTOM = [ent.Direction.DOWN] * 3

        # Math tools
        self.sqrt = math.sqrt
        self.sin = math.sin
        self.cos = math.cos
        self.tan = math.tan
        self.pi = math.pi
        self.floor = math.floor
        self.ceil = math.ceil
        self.abs = abs  # built-in abs function
        self.pow = pow  # built-in pow function

        # Type hints
        self.Optional = Optional
        self.Union = Union
        self.List = List
        self.Dict = Dict
        self.Tuple = Tuple
        self.Set = Set

        # Get all classes from the entities module
        entity_module = sys.modules[Entity.__module__]

        # Find all classes that inherit from BaseModel (which includes Entity and its subclasses)
        entity_classes = inspect.getmembers(
            entity_module,
            lambda member: (
                inspect.isclass(member)
                and issubclass(member, BaseModel)
                and member != BaseModel
            ),
        )

        # Add each entity class to both the namespace and persistent vars
        for name, entity_class in entity_classes:
            setattr(self, name, entity_class)

        # Add all the members of this class as static members so they can be accessed by the agent program.
        self._static_members = [
            attr
            for attr in dir(self)
            if not callable(getattr(self, attr)) and not attr.startswith("__")
        ]

    def get_functions(self) -> List[SerializableFunction]:
        """
        Gets all defined functions mapped from their attribute name in the namespace.
        @return:
        """
        # return [SerializableFunction(name=name, func=getattr(self, name)) for name in dir(self) if callable(getattr(self, name)) and not name.startswith("__")]
        return list(
            filter(
                lambda x: isinstance(x, SerializableFunction),
                self.persistent_vars.values(),
            )
        )

    def load(self, namespace_str: bytes):
        try:
            env = pickle.loads(namespace_str)
            for key, value in env.items():
                # Unwrap any serialized values (like functions)
                restored_value = unwrap_after_deserialization(self, value)
                self.persistent_vars[key] = restored_value
                setattr(self, key, restored_value)

        except Exception as e:
            print(f"Error restoring namespace: {e}")
            pass

    def _assign_target(self, target, value, eval_dict):
        """Helper function to handle different types of assignment targets"""
        if isinstance(target, ast.Name):
            eval_dict[target.id] = value
        elif isinstance(target, ast.Tuple):
            if not isinstance(value, (tuple, list)) or len(target.elts) != len(value):
                raise ValueError("Cannot unpack - length mismatch")
            for t, v in zip(target.elts, value):
                self._assign_target(t, v, eval_dict)
        elif isinstance(target, ast.List):
            if not isinstance(value, (tuple, list)) or len(target.elts) != len(value):
                raise ValueError("Cannot unpack - length mismatch")
            for t, v in zip(target.elts, value):
                self._assign_target(t, v, eval_dict)
        else:
            raise SyntaxError(f"Unsupported target type: {type(target)}")

    def reset(self):
        """
        Delete all variables that have accrued in the namespace by the agent, except for preexisting members
        @return:
        """
        for attr in dir(self):
            if (
                not callable(getattr(self, attr))
                and attr[0] != "_"
                and attr not in self._static_members
            ):
                self[attr] = None

    def __getitem__(self, key):
        if key not in dir(self) or key.startswith("__"):
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def log(self, *arg):
        if self.execution_trace:
            self.log_counter += 1  # Increment counter
            self.logging_results[self.log_counter] = [
                (self.line_value, repr(arg))
            ]  # Store line number with the log

        else:
            if self.line_value not in self.logging_results:
                self.logging_results[self.line_value] = []
            self.logging_results[self.line_value].append(repr(arg))

        # if 'error' in repr(arg).lower():
        #     print(f"\033[93m{self.tcp_port}: {repr(arg)}\x1b[0m")
        # else:
        #     print(f"\033[0m{self.tcp_port}: {repr(arg)}\x1b[0m")
        return None  # Return None instead of the args

    def _get_suggestions_from_name_error(
        self, eval_dict, error_msg
    ) -> List[Tuple[str, str]]:
        try:
            # Safely extract variable name from error message
            if "'" in error_msg:
                var_name = error_msg.split("'")[1]
            else:
                # Fallback: return empty list if we can't parse the error message
                return []

            # Get available variables from both eval_dict and class attributes
            available_vars = {}

            # Add variables from eval_dict with their types
            for name, value in eval_dict.items():
                if not name.startswith("_"):
                    available_vars[name] = value

            # Add class attributes
            for name in dir(self):
                if not name.startswith("_"):
                    try:
                        available_vars[name] = getattr(self, name)
                    except Exception:
                        # Skip attributes that can't be accessed
                        continue

            # Get close matches using difflib
            matches = get_close_matches(var_name, available_vars.keys(), n=3, cutoff=0.6)

            # Create suggestions with type information
            suggestions = []
            for match in matches:
                try:
                    value = available_vars[match]
                    type_hint = get_value_type_str(value)
                    suggestions.append((match, type_hint))
                except Exception:
                    # If we can't get type info, still include the suggestion without type
                    suggestions.append((match, "unknown type"))

            return suggestions
        except Exception:
            # If anything goes wrong, return empty list rather than crashing
            return []

    def _extract_error_lines(self, expr, traceback_str):
        lines = expr.splitlines()
        error_lines = []
        for line in traceback_str.splitlines():
            if 'File "file", line' in line:
                line_num = int(line.split(", line")[1].split(",")[0])
                if 1 <= line_num <= len(lines):
                    error_lines.append((line_num, lines[line_num - 1].strip()))
        return error_lines

    def _change_print_to_log(self, node):
        if isinstance(node, ast.Expr):
            # check if its print, if it is, then we route to log
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "print"
            ):
                # change print to log function
                node.value.func.id = "log"

            elif (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "time.sleep"
            ):
                # change print to log function
                node.value.func.id = "sleep"

        elif (
            isinstance(node, ast.If)
            or isinstance(node, ast.For)
            or isinstance(node, ast.While)
        ):
            for subnode_idx, subnode in enumerate(node.body):
                node.body[subnode_idx] = self._change_print_to_log(subnode)
            for subnode_idx, subnode in enumerate(node.orelse):
                node.orelse[subnode_idx] = self._change_print_to_log(subnode)
        elif isinstance(node, ast.FunctionDef):
            for subnode_idx, subnode in enumerate(node.body):
                node.body[subnode_idx] = self._change_print_to_log(subnode)
        return node

    def execute_body(self, body, eval_dict, parent_node=None):
        """Execute a sequence of nodes while maintaining line numbers"""
        for n in body:
            n = self._change_print_to_log(n)
            result = self.execute_node(n, eval_dict, parent_node)

            # Handle break/continue propagation
            if isinstance(result, bool) and not result:
                if self.loop_context.state in ("BREAK", "CONTINUE"):
                    return False

            # Handle return statement propagation
            elif (
                isinstance(result, tuple) and len(result) == 2 and result[0] == "RETURN"
            ):
                return result

        return True

    def execute_node(self, node, eval_dict, parent_node=None):
        """
        Helper function to execute a single AST node
        Returns: True for normal execution, False or string for control flow changes
        """

        def process_annotation(annotation, eval_dict):
            """Process a type annotation node and return the evaluated type"""
            if annotation is None:
                return None

            # Handle string literals for forward references
            if isinstance(annotation, ast.Constant) and isinstance(
                annotation.value, str
            ):
                return annotation.value

            # Handle basic types (like int, str, etc)
            if isinstance(annotation, ast.Name):
                return eval_dict.get(annotation.id, annotation.id)

            # Handle subscripted types (like List[int], Dict[str, int])
            if isinstance(annotation, ast.Subscript):
                base_type = process_annotation(annotation.value, eval_dict)
                if isinstance(annotation.slice, ast.Tuple):
                    type_args = [
                        process_annotation(arg, eval_dict)
                        for arg in annotation.slice.elts
                    ]
                    return f"{base_type}[{', '.join(map(str, type_args))}]"
                else:
                    type_arg = process_annotation(annotation.slice, eval_dict)
                    return f"{base_type}[{type_arg}]"

            try:
                compiled = compile(ast.Expression(annotation), "annotation", "eval")
                return eval(compiled, eval_dict)
            except Exception:
                return ast.unparse(annotation)

        if hasattr(node, "lineno"):
            self.line_value = node.lineno

        if isinstance(node, ast.Break):
            return self.loop_context.handle_break()

        elif isinstance(node, ast.Continue):
            return self.loop_context.handle_continue()

        elif isinstance(node, ast.For):
            try:
                self.loop_context.enter_loop(node)
                iter_obj = eval(
                    compile(ast.Expression(node.iter), "file", "eval"), eval_dict
                )
                for item in iter_obj:
                    self._assign_target(node.target, item, eval_dict)
                    result = self.execute_body(node.body, eval_dict, node)

                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result

                    if self.loop_context.state == "BREAK":
                        break
                    if self.loop_context.state == "CONTINUE":
                        self.loop_context.state = "NORMAL"
                        continue

                if node.orelse and self.loop_context.state != "BREAK":
                    result = self.execute_body(node.orelse, eval_dict, node)
                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result
                return True
            finally:
                self.loop_context.exit_loop()

        elif isinstance(node, ast.While):
            self.loop_context.enter_loop(node)
            try:
                while eval(
                    compile(ast.Expression(node.test), "file", "eval"), eval_dict
                ):
                    result = self.execute_body(node.body, eval_dict, node)

                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result

                    if self.loop_context.state == "BREAK":
                        break
                    if self.loop_context.state == "CONTINUE":
                        self.loop_context.state = "NORMAL"
                        continue

                if node.orelse and self.loop_context.state != "BREAK":
                    result = self.execute_body(node.orelse, eval_dict, node)
                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result
                return True
            finally:
                self.loop_context.exit_loop()

        elif isinstance(node, ast.If):
            # Handle if statements
            test_result = eval(
                compile(ast.Expression(node.test), "file", "eval"), eval_dict
            )
            if test_result:
                result = self.execute_body(node.body, eval_dict, node)
                # Handle return statement propagation
                if (
                    isinstance(result, tuple)
                    and len(result) == 2
                    and result[0] == "RETURN"
                ):
                    return result
            elif node.orelse:
                result = self.execute_body(node.orelse, eval_dict, node)
                # Handle return statement propagation
                if (
                    isinstance(result, tuple)
                    and len(result) == 2
                    and result[0] == "RETURN"
                ):
                    return result
            return True

        elif isinstance(node, ast.FunctionDef):
            try:
                # Process return type annotation if present
                return_annotation = (
                    process_annotation(node.returns, eval_dict)
                    if node.returns
                    else None
                )

                # Process argument annotations
                arg_annotations = {}

                # Handle positional args
                for arg in node.args.args:
                    if arg.annotation:
                        arg_annotations[arg.arg] = process_annotation(
                            arg.annotation, eval_dict
                        )

                # Handle keyword only args
                for arg in node.args.kwonlyargs:
                    if arg.annotation:
                        arg_annotations[arg.arg] = process_annotation(
                            arg.annotation, eval_dict
                        )

                # Handle positional only args if they exist
                for arg in getattr(node.args, "posonlyargs", []):
                    if arg.annotation:
                        arg_annotations[arg.arg] = process_annotation(
                            arg.annotation, eval_dict
                        )

                # Handle variadic args
                if node.args.vararg and node.args.vararg.annotation:
                    arg_annotations["*" + node.args.vararg.arg] = process_annotation(
                        node.args.vararg.annotation, eval_dict
                    )

                # Handle variadic kwargs
                if node.args.kwarg and node.args.kwarg.annotation:
                    arg_annotations["**" + node.args.kwarg.arg] = process_annotation(
                        node.args.kwarg.annotation, eval_dict
                    )

                # Store annotations in function's metadata
                setattr(
                    node,
                    "__annotations__",
                    {"return": return_annotation, "args": arg_annotations},
                )

                # Create function namespace that shares globals properly
                function_namespace = {**self.essential_builtins, **eval_dict}

                wrapped_node = ast.Module([node], type_ignores=[])
                compiled = compile(wrapped_node, "file", "exec")
                exec(
                    compiled, function_namespace, eval_dict
                )  # Pass eval_dict as globals

                func = function_namespace[node.name]

                if hasattr(node, "__annotations__"):
                    func.__annotations__ = getattr(node, "__annotations__")

                serialized_func = SerializableFunction(func, self)
                self.persistent_vars[node.name] = serialized_func
                setattr(self, node.name, serialized_func)
                eval_dict[node.name] = serialized_func

                return True
            except Exception:
                # If function definition fails, fall back to exec()
                compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
                exec(compiled, eval_dict)

                # Store the function in persistent vars if it was created
                if node.name in eval_dict:
                    func = eval_dict[node.name]
                    if callable(func):
                        self.persistent_vars[node.name] = wrap_for_serialization(func)
                        setattr(self, node.name, func)
                return True

        elif isinstance(node, ast.Assign):
            # Get the original eval_dict keys before execution
            original_keys = set(eval_dict.keys())

            # Compile and execute the assignment
            compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
            exec(compiled, eval_dict)

            # Find all new or updated variables
            new_or_updated_keys = set()

            # Check explicit targets
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            new_or_updated_keys.update(targets)

            # Also check for any new variables that might have been created by function calls
            current_keys = set(eval_dict.keys())
            new_keys = current_keys - original_keys
            new_or_updated_keys.update(new_keys)

            # Persist all new or updated variables
            for name in new_or_updated_keys:
                if name in eval_dict and not name.startswith("_"):
                    value = eval_dict[name]
                    self.persistent_vars[name] = wrap_for_serialization(value)
                    setattr(self, name, value)
            return True

        elif isinstance(node, ast.AnnAssign):
            if node.value:
                compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
                exec(compiled, eval_dict)

                if isinstance(node.target, ast.Name):
                    name = node.target.id
                    if name in eval_dict:
                        value = eval_dict[name]
                        self.persistent_vars[name] = wrap_for_serialization(value)
                        setattr(self, name, value)
                        # print(f"{self.tcp_port}: Stored annotated variable {name} - {type(value)}")

            return True

        elif isinstance(node, ast.AugAssign):
            # Handle augmented assignments (+=, -=, *=, /=, //=, %=, **=, &=, |=, ^=, >>=, <<=)
            compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
            exec(compiled, eval_dict)

            # Update persistent vars for the target variable
            if isinstance(node.target, ast.Name):
                name = node.target.id
                if name in eval_dict:
                    value = eval_dict[name]
                    self.persistent_vars[name] = wrap_for_serialization(value)
                    setattr(self, name, value)
                    # print(f"{self.tcp_port}: Updated augmented variable {name} = {value}")

            # Handle more complex targets like attributes or subscripts
            elif isinstance(node.target, (ast.Attribute, ast.Subscript)):
                # For attribute/subscript assignments, we need to find the base variable
                # and update it since the object may have been modified in place
                target_vars = set()

                # Extract variable names from the target expression
                def extract_names(node):
                    if isinstance(node, ast.Name):
                        target_vars.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        extract_names(node.value)
                    elif isinstance(node, ast.Subscript):
                        extract_names(node.value)
                        extract_names(node.slice)

                extract_names(node.target)

                # Update persistent vars for any variables that might have been modified
                for name in target_vars:
                    if name in eval_dict and not name.startswith("_"):
                        value = eval_dict[name]
                        self.persistent_vars[name] = wrap_for_serialization(value)
                        setattr(self, name, value)

            return True

        elif isinstance(node, ast.Expr):
            # For expressions (including function calls)
            # compiled = compile(ast.Expression(node.value), 'file', 'eval')
            #
            # try:
            #     response = eval(compiled, eval_dict, eval_dict)
            # except Exception as e:
            #     pass

            # For expressions (including function calls)
            if isinstance(node.value, ast.Call) and isinstance(
                node.value.func, ast.Name
            ):
                func_name = node.value.func.id
                if func_name in eval_dict:
                    # Get the function from eval_dict
                    func = eval_dict[func_name]

                    # # If it's a serializable function, bind it
                    # if isinstance(func, SerializableFunction):
                    #     func = func.bind(self)

                    # Evaluate the arguments
                    args = []
                    kwargs = {}
                    for arg in node.value.args:
                        args.append(
                            eval(
                                compile(ast.Expression(arg), "file", "eval"),
                                eval_dict,
                                eval_dict,
                            )
                        )
                    for keyword in node.value.keywords:
                        key = keyword.arg
                        value = eval(
                            compile(ast.Expression(keyword.value), "file", "eval"),
                            eval_dict,
                            eval_dict,
                        )
                        kwargs[key] = value

                    # Call the function and let exceptions propagate
                    response = func(*args, **kwargs)

                    # After function call, sync any changes from SerializableFunction globals back to eval_dict
                    if (
                        isinstance(func, SerializableFunction)
                        and hasattr(func, "_cached_func")
                        and func._cached_func
                    ):
                        # Get the function's globals and update our eval_dict with any changes
                        func_globals = func._cached_func.__globals__
                        for name, value in func_globals.items():
                            if not name.startswith("_") and name in eval_dict:
                                if eval_dict[name] != value:
                                    eval_dict[name] = value
                                    self.persistent_vars[name] = wrap_for_serialization(
                                        value
                                    )
                                    setattr(self, name, value)
            else:
                # For non-function call expressions
                compiled = compile(ast.Expression(node.value), "file", "eval")
                response = eval(compiled, eval_dict, eval_dict)

            # Only log if it's not a print statement (which has already been converted to log)
            if self.capture_whole_output:
                if not (
                    isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id == "print"
                ):
                    if (
                        response is not True
                        and response is not None
                        and not isinstance(node.value, ast.Constant)
                    ):
                        self._sequential_exception_count = 0

                        self.log(response)

            return True

        elif isinstance(node, ast.Return):
            # Handle return statements
            if node.value:
                # Return with a value
                return_value = eval(
                    compile(ast.Expression(node.value), "file", "eval"), eval_dict
                )
                return ("RETURN", return_value)
            else:
                # Return without a value (return None)
                return ("RETURN", None)

        elif isinstance(node, ast.Raise):
            # Handle raise statements
            if node.exc:
                # Raise with an exception
                exception = eval(
                    compile(ast.Expression(node.exc), "file", "eval"), eval_dict
                )
                if node.cause:
                    # Raise with 'from' clause
                    cause = eval(
                        compile(ast.Expression(node.cause), "file", "eval"), eval_dict
                    )
                    raise exception from cause
                else:
                    # Simple raise
                    raise exception
            else:
                # Re-raise current exception
                raise

        elif isinstance(node, ast.Assert):
            # Handle assertion statements
            test_result = eval(
                compile(ast.Expression(node.test), "file", "eval"), eval_dict
            )
            if not test_result:
                if node.msg:
                    # Assert with custom message
                    msg = eval(
                        compile(ast.Expression(node.msg), "file", "eval"), eval_dict
                    )
                    raise AssertionError(msg)
                else:
                    # Assert without message
                    raise AssertionError()
            return True

        elif isinstance(node, ast.Import):
            # Handle import statements (import module)
            for alias in node.names:
                try:
                    # Import the top-level module
                    parts = alias.name.split(".")
                    top_module = __import__(alias.name)

                    if alias.asname:
                        # If there's an alias, assign the final module to the alias
                        final_module = top_module
                        for part in parts[1:]:
                            final_module = getattr(final_module, part)
                        eval_dict[alias.asname] = final_module
                        self.persistent_vars[alias.asname] = final_module
                        setattr(self, alias.asname, final_module)
                    else:
                        # For dotted imports like "import os.path", we need to make "os" available
                        # so that "os.path" works
                        top_name = parts[0]
                        eval_dict[top_name] = top_module
                        self.persistent_vars[top_name] = top_module
                        setattr(self, top_name, top_module)

                except ImportError:
                    # Let import errors propagate naturally
                    raise
            return True

        elif isinstance(node, ast.ImportFrom):
            # Handle from-import statements (from module import name)
            try:
                # Import the module
                module_name = node.module if node.module else ""
                level = node.level if node.level else 0

                if level > 0:
                    # Relative import - requires proper package context
                    # For now, fall back to exec() as relative imports are complex
                    compiled = compile(
                        ast.Module([node], type_ignores=[]), "file", "exec"
                    )
                    exec(compiled, eval_dict)
                else:
                    # Absolute import
                    if node.names[0].name == "*":
                        # from module import * - fall back to exec()
                        compiled = compile(
                            ast.Module([node], type_ignores=[]), "file", "exec"
                        )
                        exec(compiled, eval_dict)
                        # Update persistent vars with new imports
                        # Protect essential functions from being overwritten
                        protected_names = {
                            "log",
                            "print",
                        }  # Add other essential functions as needed
                        for name, value in eval_dict.items():
                            if (
                                not name.startswith("_")
                                and name not in self.persistent_vars
                                and name not in protected_names
                            ):
                                self.persistent_vars[name] = value
                                setattr(self, name, value)

                        # Ensure our essential functions are restored after import *
                        for name in protected_names:
                            if hasattr(self, name):
                                eval_dict[name] = getattr(self, name)
                    else:
                        # Import specific names
                        imported_names = [alias.name for alias in node.names]
                        module = __import__(module_name, fromlist=imported_names)

                        # Protect essential functions from being overwritten
                        protected_names = {
                            "log",
                            "print",
                        }  # Add other essential functions as needed
                        for alias in node.names:
                            obj = getattr(module, alias.name)
                            name = alias.asname if alias.asname else alias.name
                            if name not in protected_names:
                                eval_dict[name] = obj
                                self.persistent_vars[name] = obj
                                setattr(self, name, obj)
            except ImportError:
                # Let import errors propagate naturally
                raise
            return True

        elif isinstance(node, ast.Global):
            # Handle global declarations
            # The global statement itself doesn't do anything at execution time,
            # it just affects how names are resolved in the function
            # We can handle this with a simple pass since the function compilation
            # will handle the global semantics properly
            return True

        elif isinstance(node, ast.Nonlocal):
            # Handle nonlocal declarations
            for name in node.names:
                # Mark variables as nonlocal in current scope
                # Similar to global, this affects assignment behavior
                pass
            # For now, use fallback exec() to handle nonlocal semantics properly
            compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
            exec(compiled, eval_dict)
            return True

        elif isinstance(node, ast.Try):
            try:
                result = self.execute_body(node.body, eval_dict, node)
                # Handle return statement propagation
                if (
                    isinstance(result, tuple)
                    and len(result) == 2
                    and result[0] == "RETURN"
                ):
                    return result
            except Exception as e:
                handled = False
                for handler in node.handlers:
                    if handler.type is None or isinstance(
                        e,
                        eval(
                            compile(ast.Expression(handler.type), "file", "eval"),
                            eval_dict,
                        ),
                    ):
                        if handler.name:
                            eval_dict[handler.name] = e
                        result = self.execute_body(handler.body, eval_dict, handler)
                        # Handle return statement propagation
                        if (
                            isinstance(result, tuple)
                            and len(result) == 2
                            and result[0] == "RETURN"
                        ):
                            return result
                        handled = True
                        break

                if not handled:
                    raise
            else:
                if node.orelse:
                    result = self.execute_body(node.orelse, eval_dict, node)
                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result
            finally:
                if node.finalbody:
                    result = self.execute_body(node.finalbody, eval_dict, node)
                    # Handle return statement propagation
                    if (
                        isinstance(result, tuple)
                        and len(result) == 2
                        and result[0] == "RETURN"
                    ):
                        return result
            return True

        else:
            compiled = compile(ast.Module([node], type_ignores=[]), "file", "exec")
            exec(compiled, eval_dict)
            return True

    def eval_with_timeout(self, expr):
        """
        Executes a Python expression with a timeout and returns the result.
        Supports try-except blocks, type annotations, and nested control flows.
        """

        def parse_result_into_str(data, max_lines=64):
            result = []
            for key, values in data.items():
                if self.execution_trace:
                    for line_no, value in values:
                        result.append(f"{line_no}: {value}")
                else:
                    for value in values:
                        result.append(f"{key}: {value}")
            if len(result) > max_lines:
                result = [f"{len(result) - max_lines} lines truncated..."] + result[
                    max_lines:
                ]

            return "\n".join(result)

        def find_actual_line_number(node, code_lines):
            """Find the actual line number in the source code for a given node"""
            if not hasattr(node, "lineno"):
                return 0

            return node.lineno

        tree = ast.parse(expr)
        self.logging_results = {}
        self.line_value = 0
        self.loop_context = LoopContext()

        eval_dict = {
            **{
                name: getattr(builtins, name)
                for name in dir(builtins)
                if not name.startswith("_")
            },
            **{
                name: getattr(self, name)
                for name in dir(self)
                if not name.startswith("_")
            },
            **self.persistent_vars,
        }

        # Bind any SerializableFunction objects
        for key, value in eval_dict.items():
            if isinstance(value, SerializableFunction):
                eval_dict[key] = value.bind(self)

        last_successful_state = None

        # Execute the expression
        for index, node in enumerate(tree.body):
            try:
                node = self._change_print_to_log(node)
                result = self.execute_node(node, eval_dict)

                # Handle return statement at top level
                if (
                    isinstance(result, tuple)
                    and len(result) == 2
                    and result[0] == "RETURN"
                ):
                    # If we hit a return statement at top level, log the return value and stop execution
                    return_value = result[1]
                    if return_value is not None:
                        self.log(return_value)
                    break

                last_successful_state = dict(self.persistent_vars)
            except (Exception, NameError) as e:
                self._sequential_exception_count += 1
                error_traceback = traceback.format_exc()
                error_lines = self._extract_error_lines(expr, error_traceback)

                error_message = ""
                if error_lines:
                    error_message += "Error occurred:\n"
                    for line_num, line_content in error_lines:
                        error_message += f"  Line {line_num}: {line_content}\n"
                error_type = error_traceback.strip().split("\n")[-1]

                if (
                    isinstance(e, NameError)
                    and "name '" in str(e)
                    and "' is not defined" in str(e)
                ):
                    suggestion_tuples = self._get_suggestions_from_name_error(
                        eval_dict, str(e)
                    )
                    suggestions = [
                        f"{sug} ({_type})"
                        for sug, _type in suggestion_tuples
                    ]
                    error_message += f"\n{error_type}"
                    if suggestions:
                        error_message += f"\nDid you mean one of these?\n{suggestions}"
                    else:
                        # Provide helpful fallback when no close matches are found
                        try:
                            var_name = str(e).split("'")[1]
                            error_message += f"\nNo similar variable names found for '{var_name}'."
                            error_message += f"\nTip: Check that the variable is defined before use, or verify the spelling."
                            # Optionally show some available variables as hints
                            available_names = [name for name in eval_dict.keys() if not name.startswith("_")]
                            if available_names:
                                # Show first few available variables
                                sample_vars = sorted(available_names)[:10]
                                error_message += f"\nSome available variables: {', '.join(sample_vars)}"
                                if len(available_names) > 10:
                                    error_message += f" (and {len(available_names) - 10} more)"
                        except Exception:
                            error_message += "\nTip: Check that the variable is defined before use."
                else:
                    error_message += f"\n{error_type}"

                self.log(error_message)

                if last_successful_state is not None:
                    self.persistent_vars = last_successful_state.copy()

                # if self._sequential_exception_count >= self.max_sequential_exception_count:
                break

            eval_dict.update(self.persistent_vars)
            # Re-bind any new SerializableFunction objects after dict update
            for key, value in eval_dict.items():
                if isinstance(value, SerializableFunction):
                    eval_dict[key] = value.bind(self)

        score, goal = self.score()
        result_output = parse_result_into_str(self.logging_results)

        # if had_error:
        # raise Exception(result_output)

        return score, goal, result_output

    def get_messages(self) -> List[Dict]:
        return []

    def load_messages(self, messages: List[Dict]):
        pass


def wrap_for_serialization(value):
    """Wrap values that need special serialization handling"""
    if isinstance(value, types.FunctionType):
        # Skip builtin functions
        if value.__module__ == "builtins":
            return value

        return SerializableFunction(value)
    return value


def unwrap_after_deserialization(instance, value):
    """Unwrap serialized values back to their original form"""
    if isinstance(value, SerializableFunction):
        return value.bind(instance)
    return value
