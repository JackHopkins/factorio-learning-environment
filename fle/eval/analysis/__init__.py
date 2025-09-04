"""
Analysis utilities for Factorio Learning Environment evaluation results.

This module provides comprehensive tools for analyzing evaluation results from
large-scale experiments, including database querying, performance metrics calculation,
statistical analysis, and real-time monitoring via WandB.

Main Components:
- DatabaseAnalyzer: Query and aggregate results from PostgreSQL
- PerformanceMetrics: Calculate success rates, statistical summaries
- WandBLogger: Real-time experiment tracking and visualization
- SweepManager: Orchestrate large-scale evaluation sweeps
- ResultsVisualizer: Generate plots and analysis reports

Example usage:
    from fle.eval.analysis import DatabaseAnalyzer, PerformanceMetrics, WandBLogger

    # Analyze results for specific models and tasks
    analyzer = DatabaseAnalyzer()
    results = analyzer.get_results_by_model_and_task("gpt-4o", "iron_plate_throughput_16")

    # Calculate performance metrics
    metrics = PerformanceMetrics.calculate_task_success_rate(results)

    # Log to WandB for visualization
    logger = WandBLogger(project="factorio-eval")
    logger.log_metrics(metrics, model="gpt-4o", task="iron_plate_throughput_16")
"""

# Core analysis classes
from .database_analyzer import DatabaseAnalyzer
from .performance_metrics import PerformanceMetrics
from .wandb_logger import WandBLogger
from .sweep_manager import SweepManager, SweepConfig
from .results_visualizer import ResultsVisualizer
from .api_key_manager import (
    APIKeyManager,
    get_api_key_manager,
    create_api_keys_config_template,
)
from .server_manager import ServerManager, get_server_manager

# Utility functions
from .analysis_utils import (
    group_results_by_model,
    group_results_by_task,
    calculate_pass_at_k,
    get_trajectory_summary,
)

__all__ = [
    # Core classes
    "DatabaseAnalyzer",
    "PerformanceMetrics",
    "WandBLogger",
    "SweepManager",
    "SweepConfig",
    "ResultsVisualizer",
    "APIKeyManager",
    "ServerManager",
    # Utility functions
    "group_results_by_model",
    "group_results_by_task",
    "calculate_pass_at_k",
    "get_trajectory_summary",
    "get_api_key_manager",
    "create_api_keys_config_template",
    "get_server_manager",
]
