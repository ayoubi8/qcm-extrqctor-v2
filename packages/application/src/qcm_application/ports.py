"""Application ports implemented by infrastructure adapters in later plans."""

from typing import Protocol

from qcm_shared.contracts import ArtifactVersion, Task, TerminalEvent


class TaskQueue(Protocol):
    def enqueue(self, task: Task) -> Task:
        ...


class ArtifactStore(Protocol):
    def write_version(self, artifact_version: ArtifactVersion, content: bytes) -> ArtifactVersion:
        ...


class TerminalSink(Protocol):
    def emit(self, event: TerminalEvent) -> None:
        ...


class LlmProvider(Protocol):
    provider_key: str

    def complete_json(self, *, model_id: str, prompt: str, schema_version: str) -> dict:
        ...
