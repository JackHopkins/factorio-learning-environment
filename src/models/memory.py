import json
import os
from datetime import datetime
from enum import Enum
from typing import List, Union

from rich.console import Console

from utilities.bcolors import bcolors
from models.event import Event, EventEncoder
from models.event_type import EventType
from exceptions.insufficient_score_exception import InsufficientScoreException
from models.role_type import RoleType
from pydantic import BaseModel

class Roles(Enum):
    assistant = 'assistant'
    system = 'system'
    user = 'user'

class Slot(BaseModel):
    role: Roles
    content: str
    name: str

instructions = \
    """
1. You are the character in a game of Factorio.
2. Act on all of the warnings about idle parts of your factory, and aim to grow capacity.
3. Use '#' to think what you are planning step-by-step, before issuing your python command.
4. Be creative and efficient in your actions to maximize your score by building a factory that can automatically produce items.
"""
# 4. Inspect your inventory and surroundings frequently to be sure of what's happening in the game.
# 4. On the map, you are called 'player_character'.
# 2. Automate resource extraction, processing and manufacturing to increase your score.


# get execution path
execution_path = os.path.dirname(os.path.realpath(__file__))

folder_path = f'{execution_path}/../controllers'  # path to the 'controller' folder
schema = load_schema(folder_path)

entity_definitions = load_definitions(f'{execution_path}/../factorio_types.py')

brief = \
    f"""
You have access to the following API.

Types:
{entity_definitions}

Methods:
```
{schema}
``` 

Instructions:
{instructions}

To interact with your world, you must only use the methods from this python API with basic logical flow, variable assignment and arithmetic.

Regarding coordinates: 
- a more positive X value goes to the right. 
- a more positive Y value goes down.
"""
#Enclose your interaction with START``` and END``` tags."""


class Memory(object):

    def __init__(self,
                 size=10,
                 max_history=16,
                 score_threshold=5,
                 ignore_members=[],
                 run=None,
                 llama_file='llama_events.jsonl'):
        self._ignore_members = ignore_members
        self.history: List[Event] = []
        self.max_size = max_history
        self.brief = brief

        # Write the brief to a file called `current_brief.txt`
        with open('./current_brief.txt', 'w') as f:
            f.write(brief)

        self.size = size
        self.log_file = "../log/" + datetime.now().strftime("%H-%M-%d-%m-%Y") + ".log"
        self.trace_file = "../log/" + datetime.now().strftime("%H-%M-%d-%m-%Y") + ".trace"
        self.variables = {}
        self._score = []
        self.current_score = 0
        self.current_goal = ""
        self._llama_file = llama_file
        self._instruction_prompt = instructions
        self._score_threshold = score_threshold
        self.run = run
        self.console = Console()

    def __iter__(self, *args, **kwargs) -> List[Slot]:
        """
        Get a frame of messages to pass to GPT.
        :param args:
        :param kwargs:
        :return:
        """
        pass

    def _invert_if_tuple(self, value):
        if isinstance(value, tuple):
            return value[::-1]
        elif isinstance(value, dict):
            return {k: self._invert_if_tuple(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._invert_if_tuple(i) for i in value]
        else:
            return value

    def observe_variables(self, instance):
        """
        Takes the Python variables defined in the instance scope and turns them into a frame to log in the history.
        :param instance: Instance maintaining a python interpreter state.
        :return:
        """
        members = [attr for attr in dir(instance) if not callable(getattr(instance, attr)) and not attr.startswith(
            "__") and attr not in self._ignore_members]

        variable_string = ""
        for member in members:
            if member.startswith("_"):
                continue
            self.variables[member] = instance.__dict__[member]
            value = self._invert_if_tuple(instance.__dict__[member])
            variable_string += f'\n{member} = {str(value)}'

        if variable_string:
            pass
            #self._log_history(f"variables - {{\n{variable_string.strip()}\n}}; goal - {self.current_goal.strip()}", type=EventType.VARIABLE, unique=True)

    def observe_goal(self, goal):
        self.current_goal = goal

    def log_warnings(self, alerts):
        alert_string = "warnings - " + "\n- ".join(alerts)
        self._log_history(alert_string, type=EventType.WARNING, unique=True)

    def log_error(self, message, line=0):
        output = f"{bcolors.OKCYAN}({self.current_score}) {bcolors.FAIL}{message}"

        # If the previous command caused the error, truncate it to omit the code that wasn't run.
        last_commands = self.get_last_events(filters=[EventType.COMMAND])
        if last_commands:
            last_command = last_commands[0]
            lines = last_command.message.split("\n")
            last_command_lines = lines[:line + 1]
            rewritten_last_message = "\n".join(last_command_lines)
            last_command.message = rewritten_last_message

        try:
            self._log_to_file(output)
        except Exception as e:
            print(e)

        print(output)
        self._log_history(message, type=EventType.ERROR)

    def observe_command(self, message):
        output = f"{bcolors.OKCYAN}({self.current_score}) {bcolors.OKBLUE}{message}"
        self._log_to_trace(message)
        self._log_to_file(output)
        print(output)
        self._log_history(message, type=EventType.COMMAND)

    def log_to_llama(self, events, score=0):
        while events[-1].type != EventType.COMMAND:
            events = events[:-1]
        # Prepare the LLAMA object
        input = events[:-1]  # '\n'.join([event.message for event in events[:-1]])
        output = events[-1]
        llama_obj = {
            "instruction": self._instruction_prompt,
            "input": input,
            "output": output,
            "score": score
        }

        # Append the LLAMA object to the JSONL file
        with open(self._llama_file, 'a') as f:
            f.write(json.dumps(llama_obj, cls=EventEncoder) + '\n')

    def get_events(self):
        raise NotImplementedError()

    def observe_score(self, score):
        self._score = self._score[-self.max_size:]
        self._score.append(score)
        self.current_score = score
        self.run['run/score'].append(score)

    def _calculate_discounted_rewards(self, scores: List[int], discount_rate):
        """
        Calculate the discounted reward for each event.

        Parameters:
        - events: A list of dictionaries, where each dictionary has a "score" field.
        - discount_rate: The discount rate for future rewards.

        Returns: A list of discounted rewards for each event.
        """
        # Initialize a list to hold the discounted rewards
        discounted_rewards = [0] * len(scores)

        # Start from the last event and work backwards
        cumulative_reward = 0
        for i in reversed(range(len(scores))):
            # Update the cumulative reward with the current event's score
            cumulative_reward = scores[i] + discount_rate * cumulative_reward
            discounted_rewards[i] = cumulative_reward

        return discounted_rewards

    def _restart_if_no_progress(self):
        # Retrieving variables and warnings is an automatic process, and so shouldn't affect how we score the episode
        recent_history = self.get_last_events(filters=[EventType.COMMAND,
                                                       EventType.ERROR,
                                                       EventType.OBSERVATION], number=self._score_threshold)

        if len(recent_history) < 2:
            return

        window_score = recent_history[-1].score - recent_history[0].score
        action_score = recent_history[-1].score - recent_history[-2].score

        # Only restart if the episode has no score, and yet several steps have been taken, and the most recent event was a game response
        if window_score == 0 and \
                len(recent_history) == self._score_threshold and \
                recent_history[-1].type != EventType.COMMAND:
            print("###RESTARTING###")

            #events = self.get_events()
            all_commands = self.get_last_events(filters=[EventType.COMMAND
                                                         # EventType.ERROR,
                                                         # EventType.OBSERVATION
                                                         ])
            all_history = self.get_last_events(filters=[EventType.COMMAND,
                                                        EventType.ERROR,
                                                        EventType.OBSERVATION
                                                        ])
            diff_scores = []

            for event1, event2 in zip(all_commands[1:], all_commands):
                diff_scores.append(event1.score - event2.score)
            scores = self._calculate_discounted_rewards(diff_scores, 0.8)
            sum_score = 0

            for score, event in zip(scores, all_commands[1:]):
                event.score = score
                sum_score += score

            if sum_score > self._score_threshold:
                self.log_to_llama(all_history, score=sum_score)

            self.run['final/total'] = sum_score
            self.run['final/commands'] = len(all_commands)
            self.run['final/history'] = len(all_history)
            self.run['final/errors'] = len(self.get_last_events(filters=[EventType.ERROR]))
            self.run['final/observations'] = len(self.get_last_events(filters=[EventType.OBSERVATION]))
            self.run['final/warnings'] = len(self.get_last_events(filters=[EventType.WARNING]))
            self.run['final/variables'] = len(self.get_last_events(filters=[EventType.VARIABLE]))

            self.history = []
            raise InsufficientScoreException("Insufficient score. Resetting.")

    def log_observation(self, message):
        output = f"{bcolors.OKCYAN}({self.current_score}) {bcolors.OKGREEN}{message}"
        self._log_to_file(message)
        print(output)
        self._log_history(message, type=EventType.OBSERVATION)

    def get_messages(self, events):

        # format current_goal into the brief
        brief = self.brief + "Your Goal:\n" + self.current_goal + "\n\n"
        messages = [{"role": "system", "content": brief}]
        for event in events:
            messages += [event.to_message()]
        return messages

    def get_last_events(self, filters: Union[EventType, List[EventType]] = [], number: int = 0) -> List[Event]:
        if number == 0:
            number = len(self.history)

        if not filters:
            events = self.history[:number]
            events.reverse()
            return events

        if isinstance(filters, int):
            filters = [filters]
        matching_events = [event for event in reversed(self.history) if event.type in filters]
        if not matching_events:
            return []
        subset = matching_events[:number]
        subset.reverse()
        return subset

    def _log_to_trace(self, message):
        with open(self.trace_file, "a") as f:
            f.write(message + "\n")

    def _log_to_file(self, message):
        try:
            with open(self.log_file, "a") as f:
                f.write(message + "\n")
        except Exception as e:
            print(e)

    def _log_history(self, message, type: EventType = EventType.COMMAND, unique=False):
        if isinstance(message, dict):
            message = json.dumps(message, indent=4)

        # The commands are what the agent makes, everything else is what the system makes.
        # if type == EventType.OBSERVATION \
        #         or type == EventType.WARNING \
        #         or type == EventType.ERROR \
        #         or type == EventType.VARIABLE \
        #         or type == EventType.GOAL:
        #    role = RoleType.USER
        if type != EventType.COMMAND:
            role = RoleType.USER
        else:
            role = RoleType.ASSISTANT

        if not message:
            return

        if not unique:
            self.history.append(Event(role=role,
                                      message=message,
                                      type=type,
                                      goal=self.current_goal,
                                      score=self.current_score))
        else:
            self.history = [event for event in self.history if event.message != message]

            self.history.append(Event(role=role,
                                      message=message,
                                      type=type,
                                      goal=self.current_goal,
                                      score=self.current_score))

        self._restart_if_no_progress()
        # if self.history and self.history[-1]['role'] == role and type != "error" and type != "warning":
        #    self.history[-1]['content'] += f"\n{message}"
        # else:
        #    self.history.append({
        #        "role": role, "content": message
        #    })
