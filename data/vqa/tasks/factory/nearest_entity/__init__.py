# __init__.py - Nearest entity solver module

from data.vqa.tasks.factory.nearest_entity.solver import (
    render_factory,
    nearest_entity_questions,
)

__all__ = ["render_factory", "nearest_entity_questions"]
