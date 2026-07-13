"""Small domain value objects used by the foundation layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectRef:
    user_id: str
    project_id: str

    def __post_init__(self) -> None:
        if not self.user_id or not self.project_id:
            raise ValueError("ProjectRef requires user_id and project_id")


@dataclass(frozen=True, slots=True)
class RunRef(ProjectRef):
    run_id: str

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.run_id:
            raise ValueError("RunRef requires run_id")
