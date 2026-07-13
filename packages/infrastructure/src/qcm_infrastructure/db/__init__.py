"""Database adapter package reserved for Supabase/Postgres repositories."""

from qcm_infrastructure.db.repositories import SupabaseProjectRepository, SupabaseTaskRepository

__all__ = ["SupabaseProjectRepository", "SupabaseTaskRepository"]
