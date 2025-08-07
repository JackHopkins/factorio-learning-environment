# fle/env/game/config.py

import os
from typing import Dict, Optional, Any
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
# from pydantic_settings import BaseSettings


class GameConfig(BaseModel):
    """Central configuration for the Factorio game environment using Pydantic Settings"""
    
    # Core game settings
    peaceful: bool = Field(default=True, description="Peaceful mode (no enemies)")
    all_technologies_researched: bool = Field(default=True, description="Start with all technologies researched")
    fast_mode: bool = Field(default=True, description="Enable fast mode")
    num_agents: int = Field(default=1, ge=1, description="Number of agents")
    
    # Performance and limits
    chunk_size: int = Field(default=32, description="Chunk size for map operations")
    max_samples: int = Field(default=5000, description="Maximum samples for analysis")
    max_sequential_exception_count: int = Field(default=1, description="Max sequential exceptions before stopping")
    
    # Inventory and starting conditions
    initial_inventory: Dict[str, int] = Field(default_factory=dict, description="Initial inventory for agents")
    
    # Environment variables and paths
    factorio_path: Optional[Path] = Field(default=None, description="Path to Factorio installation")
    mods_path: Optional[Path] = Field(default=None, description="Path to Factorio mods")
    saves_path: Optional[Path] = Field(default=None, description="Path to Factorio saves")
    
    @field_validator("factorio_path", "mods_path", "saves_path", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Convert string paths to Path objects"""
        if v is not None and isinstance(v, str):
            return Path(v)
        return v
    
    @field_validator("initial_inventory", mode="before")
    @classmethod
    def validate_inventory(cls, v):
        """Validate inventory format"""
        if isinstance(v, str):
            # Try to parse as JSON if it's a string
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                raise ValueError("initial_inventory must be valid JSON")
        return v
   
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Convert config to dictionary for serialization"""
        return super().model_dump(**kwargs)
    
    def model_dump_json(self, **kwargs) -> str:
        """Convert config to JSON string"""
        return super().model_dump_json(**kwargs)
    
    @classmethod
    def model_validate_json(cls, json_str: str) -> "GameConfig":
        """Create config from JSON string"""
        return super().model_validate_json(json_str)


# Default configuration instance
DEFAULT_CONFIG = GameConfig()

# Global configuration instance that can be modified
current_config = DEFAULT_CONFIG


def get_config() -> GameConfig:
    """Get the current configuration"""
    return current_config


def set_config(config: GameConfig) -> None:
    """Set the current configuration"""
    global current_config
    current_config = config


def update_config(**kwargs) -> None:
    """Update specific configuration parameters"""
    global current_config
    # Create a new config with updated values
    new_config = current_config.model_copy(update=kwargs)
    set_config(new_config)


def load_config_from_file(file_path: str) -> GameConfig:
    """Load configuration from a JSON file"""
    with open(file_path, 'r') as f:
        import json
        data = json.load(f)
    return GameConfig.model_validate(data)


def save_config_to_file(config: GameConfig, file_path: str) -> None:
    """Save configuration to a JSON file"""
    with open(file_path, 'w') as f:
        f.write(config.model_dump_json(indent=2))