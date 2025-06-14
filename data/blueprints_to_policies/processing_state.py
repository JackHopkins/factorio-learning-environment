import json
import os
from dataclasses import dataclass
from typing import Dict, Set


@dataclass
class ProcessingState:
    """Tracks the current state of blueprint processing"""

    completed_blueprints: Dict[str, Set[str]]
    completed_attempts: Dict[str, Dict[str, int]]  # blueprint -> model -> attempts

    @classmethod
    def load(cls, state_file: str) -> "ProcessingState":
        """Load processing state from file"""
        if os.path.exists(state_file):
            with open(state_file, "r") as f:
                data = json.load(f)
                return cls(
                    completed_blueprints=set(data["completed_blueprints"])
                    if "completed_blueprints" in data
                    else set(),
                    completed_attempts=data["completed_attempts"],
                )
        return cls(set(), {})

    def save(self, state_file: str):
        """Save current processing state to file"""
        with open(state_file, "w") as f:
            json.dump(
                {
                    "completed_blueprints": list(self.completed_blueprints),
                    "completed_attempts": self.completed_attempts,
                },
                f,
            )

    def add_attempt(self, blueprint_name: str, model: str):
        """Record an attempt for a blueprint/model combination"""
        if blueprint_name not in self.completed_attempts:
            self.completed_attempts[blueprint_name] = {}
        if model not in self.completed_attempts[blueprint_name]:
            self.completed_attempts[blueprint_name][model] = 0
        self.completed_attempts[blueprint_name][model] += 1

    def get_attempts(self, blueprint_name: str, model: str) -> int:
        """Get number of attempts for a blueprint/model combination"""
        return self.completed_attempts.get(blueprint_name, {}).get(model, 0)

    def mark_complete(self, blueprint_name: str):
        """Mark a blueprint as completely processed"""
        self.completed_blueprints.add(blueprint_name)
