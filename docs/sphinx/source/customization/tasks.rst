Creating Custom Tasks
======================

When adding new evaluation tasks to FLE, you need to create a task definition that inherits from the ``TaskABC`` base class and implements the required methods.

Task Structure
--------------

Create a new file in ``eval/tasks/task_definitions/``:

.. code-block:: python

   from fle.eval.tasks.task_abc import TaskABC
   from fle.env.instance import FactorioInstance
   from typing import Dict, Any

   class MyCustomTask(TaskABC):
       def __init__(self):
           super().__init__()
           self.name = "my_custom_task"
           self.description = "Description of what this task does"
           
       def setup(self, instance: FactorioInstance) -> None:
           """Initialize task environment"""
           pass
           
       def verify(self, score: float, step: int, instance: FactorioInstance, 
                  step_statistics: Dict) -> bool:
           """Verify task completion"""
           return False

Required Methods
----------------

setup(instance: FactorioInstance) -> None
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Initialize the task environment. This method is called when the task starts.

.. code-block:: python

   def setup(self, instance: FactorioInstance) -> None:
       """Initialize task environment"""
       # Set initial conditions
       # Place starting resources
       # Configure environment settings
       pass

verify(score: float, step: int, instance: FactorioInstance, step_statistics: Dict) -> bool
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Verify if the task has been completed successfully.

.. code-block:: python

   def verify(self, score: float, step: int, instance: FactorioInstance, 
              step_statistics: Dict) -> bool:
       """Verify task completion based on score and step count at step N."""
       # Check success criteria
       # Return True if task is complete
       return False

Task Components
---------------

Initial Conditions
^^^^^^^^^^^^^^^^^^

Define the starting state of the environment:

.. code-block:: python

   def setup(self, instance: FactorioInstance) -> None:
       """Initialize task environment"""
       # Place resource patches
       instance.place_resource_patch(Resource.IronOre, Position(0, 0), 10000)
       instance.place_resource_patch(Resource.Coal, Position(10, 0), 5000)
       
       # Set starting inventory
       instance.set_player_inventory({
           'iron-ore': 100,
           'coal': 50
       })
       
       # Configure game settings
       instance.set_game_speed(1.0)
       instance.set_evolution_factor(0.1)

Success Criteria
^^^^^^^^^^^^^^^^

Define what constitutes task completion:

.. code-block:: python

   def verify(self, score: float, step: int, instance: FactorioInstance, 
              step_statistics: Dict) -> bool:
       """Verify task completion"""
       # Check production rate
       if 'iron-plate' in step_statistics:
           production_rate = step_statistics['iron-plate']['production_rate']
           if production_rate >= 16:  # 16 items per minute
               return True
       
       # Check time limit
       if step > 3600:  # 1 hour time limit
           return False
           
       return False

Time Limits
^^^^^^^^^^^

Set appropriate time limits for the task:

.. code-block:: python

   def __init__(self):
       super().__init__()
       self.name = "iron_plate_throughput"
       self.description = "Produce 16 iron plates per 60 seconds"
       self.time_limit = 3600  # 1 hour in seconds
       self.max_steps = 3600   # Maximum number of steps

Resource Constraints
^^^^^^^^^^^^^^^^^^^^

Define resource availability and constraints:

.. code-block:: python

   def setup(self, instance: FactorioInstance) -> None:
       """Initialize task environment"""
       # Limited resources
       instance.place_resource_patch(Resource.IronOre, Position(0, 0), 5000)
       instance.place_resource_patch(Resource.Coal, Position(10, 0), 1000)
       
       # No other resources available
       instance.disable_resource_spawning()
       
       # Set starting technology
       instance.set_research_progress(['automation'])

Scoring Mechanism
^^^^^^^^^^^^^^^^^

Define how the task is scored:

.. code-block:: python

   def calculate_score(self, step_statistics: Dict) -> float:
       """Calculate task score"""
       if 'iron-plate' not in step_statistics:
           return 0.0
           
       production_rate = step_statistics['iron-plate']['production_rate']
       target_rate = 16.0  # items per minute
       
       # Score based on how close to target rate
       if production_rate >= target_rate:
           return 1.0
       else:
           return production_rate / target_rate

Task Examples
-------------

Simple Production Task
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class IronPlateTask(TaskABC):
       def __init__(self):
           super().__init__()
           self.name = "iron_plate_production"
           self.description = "Produce 100 iron plates"
           self.time_limit = 1800  # 30 minutes
           
       def setup(self, instance: FactorioInstance) -> None:
           """Initialize task environment"""
           # Place iron ore patch
           instance.place_resource_patch(Resource.IronOre, Position(0, 0), 10000)
           
           # Set starting inventory
           instance.set_player_inventory({'iron-ore': 200})
           
           # Enable basic technology
           instance.set_research_progress(['automation'])
           
       def verify(self, score: float, step: int, instance: FactorioInstance, 
                  step_statistics: Dict) -> bool:
           """Verify task completion"""
           if 'iron-plate' in step_statistics:
               total_produced = step_statistics['iron-plate']['total_produced']
               if total_produced >= 100:
                   return True
                   
           return False

Complex Automation Task
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   class ElectronicCircuitTask(TaskABC):
       def __init__(self):
           super().__init__()
           self.name = "electronic_circuit_automation"
           self.description = "Automate electronic circuit production"
           self.time_limit = 3600  # 1 hour
           
       def setup(self, instance: FactorioInstance) -> None:
           """Initialize task environment"""
           # Place resource patches
           instance.place_resource_patch(Resource.IronOre, Position(0, 0), 15000)
           instance.place_resource_patch(Resource.Coal, Position(10, 0), 10000)
           
           # Set starting inventory
           instance.set_player_inventory({
               'iron-ore': 500,
               'coal': 200
           })
           
           # Enable required technology
           instance.set_research_progress(['automation', 'electronics'])
           
       def verify(self, score: float, step: int, instance: FactorioInstance, 
                  step_statistics: Dict) -> bool:
           """Verify task completion"""
           if 'electronic-circuit' in step_statistics:
               production_rate = step_statistics['electronic-circuit']['production_rate']
               if production_rate >= 5:  # 5 circuits per minute
                   return True
                   
           return False

Task Registration
-----------------

Register your task with the system:

.. code-block:: python

   # In eval/tasks/task_definitions/__init__.py
   from .my_custom_task import MyCustomTask

   ALL_TASKS = [
       MyCustomTask(),
       # ... other tasks
   ]

Testing Tasks
-------------

Create test cases for your task:

.. code-block:: python

   # In eval/tasks/tests/test_my_custom_task.py
   import pytest
   from fle.eval.tasks.task_definitions.my_custom_task import MyCustomTask
   from fle.env.instance import FactorioInstance

   def test_my_custom_task_setup():
       """Test task setup"""
       task = MyCustomTask()
       instance = FactorioInstance()
       
       # Test setup doesn't raise exceptions
       task.setup(instance)
       
       # Verify initial conditions
       assert instance.get_resource_count(Resource.IronOre) > 0

   def test_my_custom_task_verification():
       """Test task verification"""
       task = MyCustomTask()
       instance = FactorioInstance()
       
       # Setup task
       task.setup(instance)
       
       # Test verification logic
       step_statistics = {'iron-plate': {'production_rate': 20}}
       result = task.verify(1.0, 100, instance, step_statistics)
       assert result is True

Best Practices
--------------

1. **Clear Success Criteria**: Define measurable success criteria
2. **Appropriate Difficulty**: Balance challenge with achievability
3. **Resource Management**: Consider resource constraints and availability
4. **Time Limits**: Set reasonable time limits for completion
5. **Testing**: Create comprehensive test cases
6. **Documentation**: Document task purpose and requirements
7. **Progressive Difficulty**: Consider multiple difficulty levels
8. **Error Handling**: Handle edge cases and error conditions
9. **Performance**: Consider computational requirements
10. **Validation**: Test with multiple agent types
