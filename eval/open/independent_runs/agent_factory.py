import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, Type, Optional, List, Any

from agents.agent_abc import AgentABC


class AgentFactory:
    """
    Factory that dynamically loads agent classes based on their absolute location.
    """

    # Dictionary to cache agent classes once they're loaded
    _agent_classes: Dict[str, Type[AgentABC]] = {}

    @classmethod
    def discover_agents(cls, agents_dir: str = None) -> Dict[str, Type[AgentABC]]:
        """
        Discover and load all agent classes from the specified directory.

        Args:
            agents_dir: Directory path to search for agent classes.
                       Defaults to the 'agents' directory.

        Returns:
            Dictionary mapping agent names to their classes
        """
        if agents_dir is None:
            # Get the directory where agents are located
            agents_dir = Path(Path(os.path.dirname(__file__)).parent.parent.parent, "agents")
        else:
            agents_dir = Path(agents_dir)

        # Clear existing cache if rediscovering
        cls._agent_classes = {}

        # Get all Python files in the agents directory
        agent_files = list(agents_dir.glob("*.py"))

        # Add other directories to search (excluding __pycache__ and similar)
        subdirs = [d for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        for subdir in subdirs:
            agent_files.extend(list(subdir.glob("*.py")))

        # Import each module and find agent classes
        for file_path in agent_files:
            # Skip __init__.py and similar
            if file_path.name.startswith("__"):
                continue

            # Determine the module name
            relative_path = file_path.relative_to(agents_dir.parent)
            module_path = str(relative_path).replace("/", ".").replace("\\", ".").replace(".py", "")

            try:
                # Import the module
                module = importlib.import_module(module_path)

                # Find all classes in the module that inherit from AgentABC
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and
                            issubclass(obj, AgentABC) and
                            obj is not AgentABC):
                        # Store the class with its name as the key
                        cls._agent_classes[name] = obj

            except Exception as e:
                print(f"Error loading agent module {module_path}: {e}")

        return cls._agent_classes

    @classmethod
    def get_available_agents(cls) -> List[str]:
        """
        Get a list of available agent names.

        Returns:
            List of available agent names
        """
        if not cls._agent_classes:
            cls.discover_agents()
        return list(cls._agent_classes.keys())

    @classmethod
    def create_agent(cls, agent_type: str, model: str, system_prompt: str, task: Any,
                     agent_idx: Optional[int] = None, **kwargs) -> AgentABC:
        """
        Create an agent of the specified type.

        Args:
            agent_type: Name of the agent class to instantiate
            model: LLM model to use
            system_prompt: System prompt for the agent
            task: Task for the agent to perform
            agent_idx: Optional agent index for multi-agent scenarios
            **kwargs: Additional keyword arguments to pass to the agent constructor

        Returns:
            Instantiated agent

        Raises:
            ValueError: If the agent type is not recognized
        """
        # Ensure agent classes are loaded
        if not cls._agent_classes:
            cls.discover_agents()

        # Get the agent class
        if agent_type not in cls._agent_classes:
            raise ValueError(f"Agent type '{agent_type}' not recognized. "
                             f"Available agents: {', '.join(cls._agent_classes.keys())}")

        agent_class = cls._agent_classes[agent_type]

        # Create and return the agent
        if agent_idx is not None:
            return agent_class(model=model, system_prompt=system_prompt,
                               task=task, agent_idx=agent_idx, **kwargs)
        else:
            return agent_class(model=model, system_prompt=system_prompt,
                               task=task, **kwargs)

    @classmethod
    def create_agent_from_config(cls, config: Dict[str, Any], task: Any) -> AgentABC:
        """
        Create an agent from a configuration dictionary.

        Args:
            config: Dictionary containing agent configuration
            task: Task for the agent to perform

        Returns:
            Instantiated agent
        """
        # Extract required parameters
        agent_type = config.pop("type")
        model = config.pop("model")
        system_prompt = config.pop("system_prompt", "")
        agent_idx = config.pop("agent_idx", None)

        # Create and return the agent
        return cls.create_agent(agent_type, model, system_prompt, task,
                                agent_idx=agent_idx, **config)