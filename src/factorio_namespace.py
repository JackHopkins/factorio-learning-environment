import ast
import builtins
import pickle
import traceback

from factorio_entities import Position, Direction, EntityStatus, BoundingBox, BeltGroup, Recipe
from factorio_types import Prototype, Resource, Technology, prototype_by_name
from search.model.game_state import SerializableFunction, wrap_for_serialization, GameState, \
    unwrap_after_deserialization


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

    def __init__(self, tcp_port):
        self.logging_results = {}
        self.line_value = 0
        self.persistent_vars = {}
        self.tcp_port = tcp_port
        self.max_sequential_exception_count = 1
        self._sequential_exception_count = 0
        self.log_counter = 0

        self.loop_context = LoopContext()

        # Turn this on to capture the outputs of all statements, rather than just `print` statement logs.
        self.capture_whole_output = False

        # We capture prints in order of them being run
        self.execution_trace = True

        # Available objects that the agent can interact with
        self.Prototype = Prototype
        self.Resource = Resource
        self.Direction = Direction
        self.Position = Position
        self.EntityStatus = EntityStatus
        self.BoundingBox = BoundingBox
        self.BeltGroup = BeltGroup
        self.Technology = Technology
        self.Recipe = Recipe

        self.prototype_by_name = prototype_by_name

        # Statically named directions
        self.UP, self.ABOVE, self.TOP = [Direction.UP] * 3
        self.RIGHT, self.EAST = [Direction.RIGHT] * 2
        self.LEFT, self.WEST = [Direction.LEFT] * 2
        self.DOWN, self.BELOW, self.BOTTOM = [Direction.DOWN] * 3

        # Add all the members of this class as static members so they can be accessed by the agent program.
        self._static_members = [attr for attr in dir(self)
                                if not callable(getattr(self, attr))
                                and not attr.startswith("__")]

    def load(self, game_state: GameState):
        try:
            if game_state.namespace:
                env = pickle.loads(game_state.namespace)
                for key, value in env.items():
                    # Unwrap any serialized values (like functions)
                    restored_value = unwrap_after_deserialization(self, value)
                    self.persistent_vars[key] = restored_value
                    setattr(self, key, restored_value)

        except Exception as e:
            print(f"Error restoring namespace: {e}")
            pass

    def reset(self):
        """
        Delete all variables that have accrued in the namespace by the agent, except for preexisting members
        @return:
        """
        for attr in dir(self):
            if not callable(getattr(self, attr)) and attr[0] != "_" and attr not in self._static_members:
                self[attr] = None

    def __getitem__(self, key):
        if key not in dir(self) or key.startswith('__'):
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def log(self, *arg):

        if self.execution_trace:
            self.log_counter += 1  # Increment counter
            self.logging_results[self.log_counter] = [(self.line_value, repr(arg))]  # Store line number with the log

        else:
            if self.line_value not in self.logging_results:
                self.logging_results[self.line_value] = []
            self.logging_results[self.line_value].append(repr(arg))

        if 'error' in repr(arg).lower():
            print(f"\033[93m{self.tcp_port}: {repr(arg)}")
        else:
            print(f"{self.tcp_port}: {repr(arg)}")
        return None  # Return None instead of the args

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
            if isinstance(node.value, ast.Call) and isinstance(node.value.func,
                                                               ast.Name) and node.value.func.id == 'print':
                # change print to log function
                node.value.func.id = 'log'

        elif isinstance(node, ast.If) or isinstance(node, ast.For) or isinstance(node, ast.While):
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
            if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
                return annotation.value

            # Handle basic types (like int, str, etc)
            if isinstance(annotation, ast.Name):
                return eval_dict.get(annotation.id, annotation.id)

            # Handle subscripted types (like List[int], Dict[str, int])
            if isinstance(annotation, ast.Subscript):
                base_type = process_annotation(annotation.value, eval_dict)
                if isinstance(annotation.slice, ast.Tuple):
                    type_args = [process_annotation(arg, eval_dict) for arg in annotation.slice.elts]
                    return f"{base_type}[{', '.join(map(str, type_args))}]"
                else:
                    type_arg = process_annotation(annotation.slice, eval_dict)
                    return f"{base_type}[{type_arg}]"

            try:
                compiled = compile(ast.Expression(annotation), 'annotation', 'eval')
                return eval(compiled, eval_dict)
            except Exception as e:
                return ast.unparse(annotation)

        if hasattr(node, 'lineno'):
            self.line_value = node.lineno

        if isinstance(node, ast.Break):
            return self.loop_context.handle_break()

        elif isinstance(node, ast.Continue):
            return self.loop_context.handle_continue()

        elif isinstance(node, ast.For):
            try:
                self.loop_context.enter_loop(node)
                iter_obj = eval(compile(ast.Expression(node.iter), 'file', 'eval'), eval_dict)
                for item in iter_obj:
                    eval_dict[node.target.id] = item
                    result = self.execute_body(node.body, eval_dict, node)

                    if self.loop_context.state == "BREAK":
                        break
                    if self.loop_context.state == "CONTINUE":
                        self.loop_context.state = "NORMAL"
                        continue

                    if node.orelse and self.loop_context.state != "BREAK":
                        self.execute_body(node.orelse, eval_dict, node)
                    return True
            finally:
                self.loop_context.exit_loop()

        elif isinstance(node, ast.While):
            self.loop_context.enter_loop(node)
            try:
                while eval(compile(ast.Expression(node.test), 'file', 'eval'), eval_dict):
                    result = self.execute_body(node.body, eval_dict, node)

                    if self.loop_context.state == "BREAK":
                        break
                    if self.loop_context.state == "CONTINUE":
                        self.loop_context.state = "NORMAL"
                        continue

                if node.orelse and self.loop_context.state != "BREAK":
                    self.execute_body(node.orelse, eval_dict, node)
                return True
            finally:
                self.loop_context.exit_loop()

        elif isinstance(node, ast.If):
            # Handle if statements
            test_result = eval(compile(ast.Expression(node.test), 'file', 'eval'), eval_dict)
            if test_result:
                self.execute_body(node.body, eval_dict, node)
            elif node.orelse:
                self.execute_body(node.orelse, eval_dict, node)
            return True

        elif isinstance(node, ast.FunctionDef):
            # Process return type annotation if present
            return_annotation = process_annotation(node.returns, eval_dict) if node.returns else None

            # Process argument annotations
            arg_annotations = {}
            defaults = {}

            # Handle positional args
            for arg in node.args.args:
                if arg.annotation:
                    arg_annotations[arg.arg] = process_annotation(arg.annotation, eval_dict)

            # Handle keyword only args
            for arg in node.args.kwonlyargs:
                if arg.annotation:
                    arg_annotations[arg.arg] = process_annotation(arg.annotation, eval_dict)

            # Handle positional only args if they exist
            for arg in getattr(node.args, 'posonlyargs', []):
                if arg.annotation:
                    arg_annotations[arg.arg] = process_annotation(arg.annotation, eval_dict)

            # Handle variadic args
            if node.args.vararg and node.args.vararg.annotation:
                arg_annotations['*' + node.args.vararg.arg] = process_annotation(node.args.vararg.annotation,
                                                                                 eval_dict)

            # Handle variadic kwargs
            if node.args.kwarg and node.args.kwarg.annotation:
                arg_annotations['**' + node.args.kwarg.arg] = process_annotation(node.args.kwarg.annotation,
                                                                                 eval_dict)

            # Store annotations in function's metadata
            setattr(node, '__annotations__', {
                'return': return_annotation,
                'args': arg_annotations
            })

            wrapped_node = ast.Module([node], type_ignores=[])
            compiled = compile(wrapped_node, 'file', 'exec')
            exec(compiled, eval_dict)

            func = eval_dict[node.name]

            if hasattr(node, '__annotations__'):
                func.__annotations__ = getattr(node, '__annotations__')

            serialized_func = SerializableFunction(func, self)
            self.persistent_vars[node.name] = serialized_func
            setattr(self, node.name, serialized_func)
            eval_dict[node.name] = serialized_func

            return True

        elif isinstance(node, ast.Assign):
            compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
            exec(compiled, eval_dict)

            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            for name in targets:
                if name in eval_dict:
                    value = eval_dict[name]
                    self.persistent_vars[name] = wrap_for_serialization(value)
                    setattr(self, name, value)
                    print(f"{self.tcp_port}: Stored variable {name} - {type(value)}")

            return True

        elif isinstance(node, ast.AnnAssign):
            if node.value:
                compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
                exec(compiled, eval_dict)

                if isinstance(node.target, ast.Name):
                    name = node.target.id
                    if name in eval_dict:
                        value = eval_dict[name]
                        self.persistent_vars[name] = wrap_for_serialization(value)
                        setattr(self, name, value)
                        print(f"{self.tcp_port}: Stored annotated variable {name} - {type(value)}")

            return True


        elif isinstance(node, ast.Expr):

            # For expressions (including function calls)
            compiled = compile(ast.Expression(node.value), 'file', 'eval')

            response = eval(compiled, eval_dict)

            # Only log if it's not a print statement (which has already been converted to log)
            if self.capture_whole_output:
                if not (isinstance(node.value, ast.Call) and

                        isinstance(node.value.func, ast.Name) and

                        node.value.func.id == 'print'):

                    if response is not True and response is not None and not isinstance(node.value, ast.Constant):
                        self._sequential_exception_count = 0

                        self.log(response)

            return True

        elif isinstance(node, ast.Try):
            try:
                self.execute_body(node.body, eval_dict, node)
            except Exception as e:
                handled = False
                for handler in node.handlers:
                    if handler.type is None or isinstance(e, eval(compile(ast.Expression(handler.type), 'file',
                                                                          'eval'), eval_dict)):
                        if handler.name:
                            eval_dict[handler.name] = e
                        self.execute_body(handler.body, eval_dict, handler)
                        handled = True
                        break

                if not handled:
                    raise
            else:
                if node.orelse:
                    self.execute_body(node.orelse, eval_dict, node)
            finally:
                if node.finalbody:
                    self.execute_body(node.finalbody, eval_dict, node)
            return True

        else:
            compiled = compile(ast.Module([node], type_ignores=[]), 'file', 'exec')
            exec(compiled, eval_dict)
            return True

    def eval_with_timeout(self, expr):
        """
        Executes a Python expression with a timeout and returns the result.
        Supports try-except blocks, type annotations, and nested control flows.
        """

        def parse_result_into_str(data):
            result = []
            for key, values in data.items():
                if self.execution_trace:
                    for line_no, value in values:
                        result.append(f"{line_no}: {value}")
                else:
                    for value in values:
                        result.append(f"{key}: {value}")
            return "\n".join(result)

        def find_actual_line_number(node, code_lines):
            """Find the actual line number in the source code for a given node"""
            if not hasattr(node, 'lineno'):
                return 0

            return node.lineno


        tree = ast.parse(expr)
        self.logging_results = {}
        self.line_value = 0
        self.loop_context = LoopContext()

        eval_dict = {
            **{name: getattr(builtins, name) for name in dir(builtins) if not name.startswith('_')},
            **{name: getattr(self, name) for name in dir(self) if not name.startswith('_')},
            **self.persistent_vars
        }

        last_successful_state = None
        had_error = False

        # Execute the expression
        for index, node in enumerate(tree.body):
            try:
                node = self._change_print_to_log(node)
                self.execute_node(node, eval_dict)
                last_successful_state = dict(self.persistent_vars)

            except Exception as e:
                had_error = True
                self._sequential_exception_count += 1
                error_traceback = traceback.format_exc()
                error_lines = self._extract_error_lines(expr, error_traceback)

                error_message = ""
                if error_lines:
                    error_message += "Error occurred:\n"
                    for line_num, line_content in error_lines:
                        error_message += f"  Line {line_num}: {line_content}\n"
                error_type = error_traceback.strip().split('\n')[-1]
                error_message += f"\n{error_type}"

                self.log(error_message)

                if last_successful_state is not None:
                    self.persistent_vars = last_successful_state.copy()

                if self._sequential_exception_count >= self.max_sequential_exception_count:
                    break

            eval_dict.update(self.persistent_vars)

        score, goal = self.score()
        result_output = parse_result_into_str(self.logging_results)

        #if had_error:
            #raise Exception(result_output)

        return score, goal, result_output