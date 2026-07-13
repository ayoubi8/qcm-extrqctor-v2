"""Compatibility helpers for Python versions used by free deploy targets."""

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python 3.10 deployment path
    from enum import Enum

    class StrEnum(str, Enum):
        """Python 3.10-compatible subset of enum.StrEnum."""
