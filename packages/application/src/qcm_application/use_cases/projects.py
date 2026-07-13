"""Project use cases."""

from qcm_domain.auth import UserContext
from qcm_shared.api_contracts import ProjectCreateCommand, ProjectSummary


def create_project(command: ProjectCreateCommand, *, user: UserContext, repository) -> ProjectSummary:
    if command.user_id != user.user_id and not user.is_admin:
        raise PermissionError("Cannot create project for another user")
    return repository.create_project(command)
