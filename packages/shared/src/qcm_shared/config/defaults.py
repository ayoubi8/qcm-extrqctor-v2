"""Shared defaults that are safe to expose as non-secret configuration."""

from dataclasses import dataclass


MAX_SOURCE_FILE_BYTES = 52_428_800
INITIAL_LLM_PROVIDER = "openrouter"


@dataclass(frozen=True, slots=True)
class TaskRuntimeDefaults:
    worker_poll_seconds: int = 5
    heartbeat_seconds: int = 30
    lease_ttl_seconds: int = 120
    retry_backoff_seconds: tuple[int, int, int] = (10, 30, 90)
    max_attempts: int = 3


DEFAULT_CONFIG = {
    "max_source_file_bytes": MAX_SOURCE_FILE_BYTES,
    "initial_llm_provider": INITIAL_LLM_PROVIDER,
    "task_runtime": TaskRuntimeDefaults(),
}
