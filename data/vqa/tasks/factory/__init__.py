# __init__.py - Factory task module

from data.vqa.tasks.factory.task import (
    nearest_entity_task,
    entity_status_task,
    factory_task,
)

__all__ = ["nearest_entity_task", "entity_status_task", "factory_task"]
