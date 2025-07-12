import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


class FLELogger:
    """
    Centralized logger for the FLE project.
    Provides different log levels and handles both file and console output.
    """
    
    _instance: Optional['FLELogger'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._setup_logger()
            FLELogger._initialized = True
    
    def _setup_logger(self):
        """Setup the logger with appropriate handlers and formatters."""
        # Create logger
        self.logger = logging.getLogger('fle')
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (rotating)
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'fle.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, *args, **kwargs)


# Global logger instance
_logger_instance = None


def get_logger() -> FLELogger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = FLELogger()
    return _logger_instance


# Convenience functions for direct usage
def debug(message: str, *args, **kwargs):
    """Log debug message."""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """Log info message."""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """Log warning message."""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """Log error message."""
    get_logger().error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """Log critical message."""
    get_logger().critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs):
    """Log exception with traceback."""
    get_logger().exception(message, *args, **kwargs)