"""Task handler registry placeholder."""

from collections.abc import Callable
from typing import Any

TaskHandler = Callable[[dict[str, Any]], dict[str, Any]]

TASK_HANDLERS: dict[str, TaskHandler] = {}


def register_handler(kind: str, handler: TaskHandler) -> None:
    if not kind:
        raise ValueError("Task handler kind is required")
    if kind in TASK_HANDLERS:
        raise ValueError(f"Task handler already registered: {kind}")
    TASK_HANDLERS[kind] = handler
