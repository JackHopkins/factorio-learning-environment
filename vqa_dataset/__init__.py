"""
Factorio Blueprint VQA Dataset Generation Package.

This package provides tools for creating Visual Question Answering (VQA) datasets
from Factorio game blueprints using the Inspect AI framework.

Components:
- blueprint_loader: Load and parse Factorio blueprint JSON files
- blueprint_renderer: Render blueprints to images using FLE environment
- question_generator: Generate VQA questions for blueprints
- inspect_solver: Inspect AI solver for VQA tasks
- dataset_pipeline: Complete pipeline for dataset generation
"""

from .blueprint_loader import Blueprint, BlueprintLoader, Entity
from .question_generator import QuestionGenerator, VQAExample
from .inspect_solver import factorio_vqa_solver, FactorioBlueprintAnalyzer
from .dataset_pipeline import VQADatasetPipeline

__version__ = "0.1.0"
__author__ = "Claude"

__all__ = [
    "Blueprint",
    "BlueprintLoader", 
    "Entity",
    "QuestionGenerator",
    "VQAExample",
    "factorio_vqa_solver",
    "FactorioBlueprintAnalyzer", 
    "VQADatasetPipeline"
]