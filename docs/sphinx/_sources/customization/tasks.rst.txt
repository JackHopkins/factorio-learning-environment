Creating Custom Tasks
=====================

FLE allows you to create custom tasks for evaluating agent capabilities. Tasks define the objectives, constraints, and success criteria for agent evaluation.

Task Structure
--------------

Tasks are defined in `fle/eval/tasks/task_definitions/` and follow a specific structure:

**Task Definition File**
   JSON configuration file defining task parameters

**Task Implementation**
   Python class implementing the task logic

**Task Registration**
   Automatic registration with the gym environment registry

Task Definition
---------------

Create a new task definition file in `fle/eval/tasks/task_definitions/`:

.. code-block:: json

   {
       "name": "my_custom_task",
       "description": "A custom task for evaluating agent capabilities",
       "type": "throughput",
       "target": 16,
       "time_limit": 3600,
       "resources": {
           "iron_ore": 10000,
           "copper_ore": 5000,
           "coal": 2000
       },
       "technologies": ["automation"],
       "constraints": {
           "max_entities": 100,
           "max_power": 1000
       }
   }

Task Types
----------

**Throughput Tasks**
   Tasks focused on producing a specific item at a target rate

**Research Tasks**
   Tasks focused on technology research and advancement

**Construction Tasks**
   Tasks focused on building specific structures

**Exploration Tasks**
   Tasks focused on map exploration and discovery

**Multi-Objective Tasks**
   Tasks with multiple competing objectives

Task Implementation
-------------------

Create a Python class implementing your task:

.. code-block:: python

   from fle.eval.tasks.base import BaseTask
   
   class MyCustomTask(BaseTask):
       def __init__(self, config):
           super().__init__(config)
           self.target = config.get('target', 16)
           self.time_limit = config.get('time_limit', 3600)
       
       def evaluate(self, state):
           """Evaluate the current state against task objectives"""
           # Implement your evaluation logic
           pass
       
       def is_complete(self, state):
           """Check if the task is complete"""
           # Implement completion criteria
           pass
       
       def get_reward(self, state):
           """Calculate reward for current state"""
           # Implement reward calculation
           pass

Task Configuration
------------------

Tasks can be configured with various parameters:

**Resource Constraints**
   - Starting resources
   - Resource availability
   - Resource consumption rates

**Technology Requirements**
   - Required technologies
   - Technology research costs
   - Technology dependencies

**Time Constraints**
   - Time limits
   - Time-based objectives
   - Time-based rewards

**Spatial Constraints**
   - Map size limits
   - Entity placement rules
   - Distance requirements

**Performance Constraints**
   - Power consumption limits
   - Entity count limits
   - Efficiency requirements

Task Registration
-----------------

Tasks are automatically registered with the gym environment registry:

1. **File Discovery**: The registry scans `fle/eval/tasks/task_definitions/`
2. **JSON Parsing**: Task definitions are parsed from JSON files
3. **Environment Creation**: Gym environments are created for each task
4. **Registration**: Environments are registered with gym

Example Task
------------

Here's a complete example of a custom task:

**Task Definition** (`my_custom_task.json`):

.. code-block:: json

   {
       "name": "iron_plate_throughput",
       "description": "Produce iron plates at 16 items per 60 seconds",
       "type": "throughput",
       "target": 16,
       "time_limit": 3600,
       "resources": {
           "iron_ore": 10000,
           "coal": 2000
       },
       "technologies": ["automation"],
       "constraints": {
           "max_entities": 50,
           "max_power": 500
       }
   }

**Task Implementation** (`my_custom_task.py`):

.. code-block:: python

   from fle.eval.tasks.base import BaseTask
   from fle.env.game_types import Entity, Inventory
   
   class IronPlateThroughputTask(BaseTask):
       def __init__(self, config):
           super().__init__(config)
           self.target = config.get('target', 16)
           self.time_limit = config.get('time_limit', 3600)
           self.start_time = None
       
       def reset(self):
           """Reset the task state"""
           self.start_time = None
           return super().reset()
       
       def evaluate(self, state):
           """Evaluate current throughput"""
           if self.start_time is None:
               self.start_time = state.get('game_info', {}).get('tick', 0)
           
           current_time = state.get('game_info', {}).get('tick', 0)
           elapsed_time = (current_time - self.start_time) / 60.0  # Convert to seconds
           
           if elapsed_time < 60:
               return 0.0
           
           # Calculate throughput
           inventory = state.get('inventory', Inventory({}))
           iron_plates = inventory.get('iron-plate', 0)
           throughput = iron_plates / elapsed_time
           
           return throughput
       
       def is_complete(self, state):
           """Check if target throughput is achieved"""
           throughput = self.evaluate(state)
           return throughput >= self.target
       
       def get_reward(self, state):
           """Calculate reward based on throughput"""
           throughput = self.evaluate(state)
           if throughput >= self.target:
               return 1.0
           else:
               return throughput / self.target

Testing Tasks
--------------

Create test cases for your custom tasks:

.. code-block:: python

   import pytest
   from fle.eval.tasks.my_custom_task import MyCustomTask
   
   def test_task_creation():
       config = {
           'target': 16,
           'time_limit': 3600
       }
       task = MyCustomTask(config)
       assert task.target == 16
       assert task.time_limit == 3600
   
   def test_task_evaluation():
       config = {'target': 16}
       task = MyCustomTask(config)
       
       # Mock state
       state = {
           'inventory': Inventory({'iron-plate': 100}),
           'game_info': {'tick': 3600}
       }
       
       throughput = task.evaluate(state)
       assert throughput > 0
   
   def test_task_completion():
       config = {'target': 16}
       task = MyCustomTask(config)
       
       # Mock state with high throughput
       state = {
           'inventory': Inventory({'iron-plate': 1000}),
           'game_info': {'tick': 3600}
       }
       
       assert task.is_complete(state)

Advanced Features
----------------

**Multi-Agent Tasks**
   Tasks that require coordination between multiple agents

**Dynamic Tasks**
   Tasks that change objectives during execution

**Hierarchical Tasks**
   Tasks with sub-objectives and dependencies

**Adaptive Tasks**
   Tasks that adjust difficulty based on agent performance

Best Practices
--------------

1. **Clear Objectives**: Define clear, measurable objectives
2. **Appropriate Difficulty**: Balance challenge with achievability
3. **Robust Evaluation**: Handle edge cases and error conditions
4. **Comprehensive Testing**: Test all task scenarios
5. **Documentation**: Document task requirements and constraints
6. **Performance**: Optimize evaluation for large-scale experiments
