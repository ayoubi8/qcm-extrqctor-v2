"""Database repository adapter shells.

Concrete Supabase/Postgres calls are wired in later plans. These classes make dependency
injection boundaries explicit for API and worker services.
"""


class SupabaseProjectRepository:
    def __init__(self, client) -> None:
        self.client = client

    def create_project(self, command):
        raise NotImplementedError("Project persistence is implemented after repository wiring")

    def list_projects(self, user):
        raise NotImplementedError("Project listing is implemented after repository wiring")

    def get_project_owner(self, project_id: str) -> str:
        raise NotImplementedError("Project owner lookup is implemented after repository wiring")


class SupabaseTaskRepository:
    def __init__(self, client) -> None:
        self.client = client

    def create_task(self, task):
        raise NotImplementedError("Task persistence is implemented in Plan 06")
