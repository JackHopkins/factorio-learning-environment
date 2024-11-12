import ast
import re
import time
from multiprocessing import freeze_support

#import neptune
from anthropic.types import Message
from backoff import on_exception, expo
from openai import OpenAI, RateLimitError, APIError
from openai.types.chat import ChatCompletion

from factorio_instance import FactorioInstance
from llm_factory import LLMFactory
from models.insufficient_score_exception import InsufficientScoreException
from models.split_memory import SplitMemory
from vocabulary import Vocabulary

"""
nearest().get("burner-mining-drill").rotate(NORTH)
nearest().place("burner-mining-drill").rotate(EAST)
at(0,0).place("burner-mining-drill").rotate(NORTH)
at(0,0).get("burner-mining-drill").
inventory.get("burner-mining-drill").place(0,0).rotate(NORTH)
"""

import openai


class FactorioRunner:

    def __init__(self,
                 llm_factory,
                 instance,
                 buffer_size=10,
                 courtesy_delay=0,
                 checkpoint=False,
                 neptune_project=None,
                 neptune_api_token=None,
                 ):

        self.buffer = {}
        self.model = llm_factory.model
        self.llm_factory: LLMFactory = llm_factory
        self.buffer_size = buffer_size
        self.max_sequential_exception_count = 3
        self.courtesy_delay = courtesy_delay
        self.neptune_project = neptune_project
        self.neptune_api_token = neptune_api_token
        self.run = neptune.init_run(
            project=self.neptune_project,
            api_token=self.neptune_api_token,
        )
        self.run["parameters"] = {
            "model": self.llm_factory.model,
            "buffer_size": buffer_size,
            "beam": self.llm_factory.beam,
            "courtesy_delay": courtesy_delay,
        }

        freeze_support()
        self.instance = instance
        self.memory = self.set_memory()
        self.history = []
        self.program_generator = self._get_program_generator
        if not checkpoint:
            pass
        else:
            self.checkpoint = checkpoint


    def set_memory(self):
        static_instance_members = [attr for attr in dir(self.instance)
                                   if not callable(getattr(self.instance, attr))
                                   and not attr.startswith("__")
                                   and getattr(self.instance, attr)]
        return SplitMemory(ignore_members=static_instance_members,
                           max_commands=self.buffer_size,
                           run=self.run,
                           score_threshold=15)

    def replay(self):
        with open(f"log/{self.checkpoint}.trace", "r") as f:
            lines = f.readlines()
            for line in lines:
                print(line)
                if line[0] != "#":
                    try:
                        score, goal, response = self.instance.eval(line.rstrip("\n;"))
                        print(response)
                    except Exception as e:
                        print(e)


    @on_exception(expo,(RateLimitError, APIError))
    def _get_program_generator(self):

        time.sleep(self.courtesy_delay)
        messages = next(self.memory)

        try:
            response = self.llm_factory.call(
                model=self.model,  # "gpt-3.5-turbo",x
                max_tokens=500,
                messages=messages,
                #stream=True
            )
        except Exception as e:
            print(e)
            raise
        return response

    def is_valid_python(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _replace_comments(self, code):
        # Regular expression pattern to match a single-line comment, capturing preceding whitespace
        pattern = r'^(\s*)(.+?)\s*# ?(.*)$|^(\s*)# ?(.*)$'

        # Callback function to replace the comment
        def comment_replacer(match):
            if match.group(1) is not None:  # Comment after code
                indent, code_part, comment_text = match.group(1, 2, 3)
                return f'{indent}{code_part}\n{indent}comment("{comment_text}")'
            else:  # Comment on its own line
                indent, comment_text = match.group(4, 5)
                return f'{indent}comment("{comment_text}")'

        # Replace comments in the code
        lines = code.split('\n')
        new_lines = [re.sub(pattern, comment_replacer, line) for line in lines]
        new_code = '\n'.join(new_lines).rstrip('\n')
        return new_code

    def _append_buffer(self):
        chunk_generator = self.program_generator()
        

        if isinstance(chunk_generator, ChatCompletion):
            for index, choice in enumerate(chunk_generator.choices):
                buffer = choice.message.content if not isinstance(choice.message, str) else choice.message
                # Remove START``` and END``` from the message
                #content = message.content.replace("START```", "").replace("END```", "")

                if not isinstance(buffer, str):
                    buffer = buffer.content

                if "START```" in buffer:
                    buffer = buffer.split("START```")[1]

                values = buffer.split("\n\n")
                # set self.buffer to be a dict indexed by the index of the choice
                for index, value in enumerate(values):
                    if index not in self.buffer:
                        self.buffer[index] = ""
                    self.buffer[index] += value+'\n'
        
        # Anthropic Support
        elif isinstance(chunk_generator, Message):
            buffer = ""
            for index, choice in enumerate(chunk_generator.content):
                if chunk_generator:
                    buffer += choice.text
                    # if 0 not in self.buffer:
                    #     self.buffer[0] = ""
                    # self.buffer[0] += choice.text
            if "START```" in buffer:
                buffer = buffer.split("START```")[1]

            values = buffer.split("\n")
            # set self.buffer to be a dict indexed by the index of the choice
            for index, value in enumerate(values):
                if index not in self.buffer:
                    self.buffer[index] = ""
                self.buffer[index] += value+'\n'
        else:
            # Accumulate the entire content
            for chunk in chunk_generator.choices:
                #choice = chunk.message.content
                chunk_message = chunk.message.content #choice['delta']
                if chunk_message.get('content'):
                    content = chunk_message.get('content')
                    if choice['index'] not in self.buffer:
                        self.buffer[choice['index']] = ""
                    self.buffer[choice['index']] += content
                    self.buffer[choice['index']] = self.buffer[choice['index']].lstrip()

    def __next__(self):
        self._append_buffer()
        # Check if the entire buffer is syntactically valid Python code
        try:
            for index, buffer in self.buffer.items():
                buffer = buffer.replace('```python', "")
                if self.is_valid_python(buffer):
                    response = self._execute_buffer(buffer)
                    if response:
                        self.memory.log_observation(response)
                    self.buffer[index] = ""
                elif self.is_valid_python("# " + buffer) and buffer[0] != "#":
                    comment_line = ("\n".join(["# "+line for line in buffer.split('\n')])+"\n")
                    self.buffer[index] = comment_line
                    #self.buffer[index] = "\n"
                else:
                    # If sampling stops part way through a line, pop the line and interpret.
                    non_valid, valid = self.split_on_last_line(buffer)
                    if self.is_valid_python(valid):
                        self._execute_buffer(valid)
                    else:
                        try:
                            pass
                            #self.memory.observe_command(buffer)
                            #self.memory.log_error("The provided code is not syntactically valid Python. Only write valid python.")
                        except InsufficientScoreException as e:
                            self._reset()

                    self.buffer[index] = ""
        except Exception as e:
            pass

    def split_on_last_line(self, s):
        if s.find("\n") != -1:
            return s[s.rfind('\n'):], s[:s.rfind('\n')]
        return "", s

    def _execute_buffer(self, buffer):

        alerts = self.instance.get_warnings()
        self.memory.observe_variables(self.instance)

        if alerts:
            try:
                self.memory.log_warnings(alerts)
            except InsufficientScoreException as e1:
                self._reset()

        buffer = self._replace_comments(buffer)
        try:
            self.memory.observe_command(buffer)
            score, goal, result = self.instance.eval(buffer.strip())
            if score != -1:
                self.memory.observe_score(score)
            self.memory.observe_goal(goal)
            if result and isinstance(result, str):
                if "Error" in result:
                    find_i = result.find(":")
                    message_i = result.rfind(":")
                    if message_i == -1:
                        message = result
                    else:
                        message = result[message_i+1:]
                    try:
                        line = int(result[:find_i])
                        self.memory.log_error(f"Error line {line}: {message.strip()}", line=line)
                    except:
                        self.memory.log_error(result)
                else:
                    self.memory.log_observation(result)
        except InsufficientScoreException as e1:
            self._reset()
            raise e1
        except Exception as e:
            try:
                error, reason = e.args
                self.memory.log_error(f"Error line {error}: {str(reason).replace('_', ' ')}", line=int(error))
            except Exception as e2:
                self.memory.log_error(f"You can't do that action. {str(e)}")
            raise e
        return result

    def _reset(self):
        self.run.stop()
        # self.run = neptune.init_run(
        #     project=self.neptune_project,
        #     api_token=self.neptune_api_token,
        # )
        self.instance.reset()
        self.memory = self.set_memory()