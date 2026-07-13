"""Retention cleanup worker helpers."""

from qcm_domain.artifacts import RETENTION_RULES
from qcm_shared.storage_contracts import CleanupCandidate


def is_cleanup_due(candidate: CleanupCandidate) -> bool:
    rule = RETENTION_RULES[candidate.retention_policy]
    return (
        candidate.delete_allowed
        and rule.cleanup_after_days is not None
        and candidate.age_days >= rule.cleanup_after_days
    )


def select_cleanup_keys(candidates: list[CleanupCandidate]) -> list[str]:
    return [candidate.storage_key for candidate in candidates if is_cleanup_due(candidate)]
