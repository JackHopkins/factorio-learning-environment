"""
Configuration for batch processing.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessingConfig:
    """Configuration for batch processing."""

    events_file_path: str
    enable_logging: bool = False
    speed: float = 1.0
    batch_size: int = 500
    max_concurrent_batches: int = 1
    enable_periodic_logging: Optional[bool] = None
    periodic_log_interval: int = 0

    def __post_init__(self):
        if self.enable_periodic_logging is None:
            self.enable_periodic_logging = self.periodic_log_interval > 0
