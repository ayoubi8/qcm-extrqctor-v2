"""Free-tier budget gates for deployment and runtime checks."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FreeTierBudget:
    max_source_file_bytes: int = 52_428_800
    supabase_database_bytes: int = 500 * 1024 * 1024
    supabase_storage_bytes: int = 1 * 1024 * 1024 * 1024
    supabase_realtime_peak_connections: int = 200
    vercel_request_body_bytes: int = 4_500_000
    hf_cpu_memory_bytes: int = 16 * 1024 * 1024 * 1024


DEFAULT_FREE_TIER_BUDGET = FreeTierBudget()


@dataclass(frozen=True, slots=True)
class UsageSample:
    source_file_bytes: int = 0
    database_bytes: int = 0
    storage_bytes: int = 0
    realtime_peak_connections: int = 0
    request_body_bytes: int = 0
    worker_memory_bytes: int = 0


def evaluate_budget(sample: UsageSample, budget: FreeTierBudget = DEFAULT_FREE_TIER_BUDGET) -> tuple[str, ...]:
    warnings: list[str] = []
    if sample.source_file_bytes > budget.max_source_file_bytes:
        warnings.append("source_file_exceeds_50mb_cap")
    if sample.database_bytes > budget.supabase_database_bytes:
        warnings.append("supabase_database_free_tier_exceeded")
    if sample.storage_bytes > budget.supabase_storage_bytes:
        warnings.append("supabase_storage_free_tier_exceeded")
    if sample.realtime_peak_connections > budget.supabase_realtime_peak_connections:
        warnings.append("supabase_realtime_connection_budget_exceeded")
    if sample.request_body_bytes > budget.vercel_request_body_bytes:
        warnings.append("vercel_request_body_limit_exceeded")
    if sample.worker_memory_bytes > budget.hf_cpu_memory_bytes:
        warnings.append("hf_worker_memory_budget_exceeded")
    return tuple(warnings)
