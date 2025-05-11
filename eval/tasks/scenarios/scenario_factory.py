import importlib.util
import inspect
import os
import sys
from pathlib import Path

from eval.tasks.scenarios.scenario_abc import ScenarioABC

SCENARIO_FOLDER = Path(os.path.dirname(__file__))


class ScenarioFactory:
    def __init__(self):
        pass

    @staticmethod
    def create_scenario(scenario_path, **kwargs) -> ScenarioABC:
        """
        Create a scenario object from a Python file path.

        Args:
            scenario_path: Path to the scenario Python file, relative to SCENARIO_FOLDER
            **kwargs: Arguments to pass to the scenario constructor

        Returns:
            An instance of the scenario class

        Raises:
            ValueError: If the scenario file doesn't exist or doesn't contain a valid scenario class
        """
        if not scenario_path[-3:]=='.py':
            scenario_path = scenario_path + '.py'

        # Convert scenario_path to an absolute path
        full_path = Path(SCENARIO_FOLDER, scenario_path)

        # Check if the file exists
        if not full_path.exists():
            raise ValueError(f"Scenario file not found: {full_path}")

        # Get module name from file path
        module_name = full_path.stem

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(module_name, full_path)
        if spec is None:
            raise ValueError(f"Could not load module spec from {full_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find scenario classes in the module (subclasses of ScenarioABC)
        scenario_classes = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                    issubclass(obj, ScenarioABC) and
                    obj != ScenarioABC):
                scenario_classes.append(obj)

        if not scenario_classes:
            raise ValueError(f"No scenario classes found in {full_path}")

        # Use the first scenario class by default
        # If there are multiple scenario classes, we could add logic to select the correct one
        scenario_class = scenario_classes[0]

        # Create an instance of the scenario class with the provided kwargs
        try:
            scenario = scenario_class(**kwargs)
            return scenario
        except Exception as e:
            raise ValueError(f"Failed to instantiate scenario class {scenario_class.__name__}: {str(e)}")