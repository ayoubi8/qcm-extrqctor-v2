"""Compatibility wrapper for canonical Step 3 correction mode mapping."""

from qcm_domain.corrections import CorrectionMode, LEGACY_CORRECTION_MODE_MAP, normalize_correction_mode

LEGACY_STEP3_MODE_MAP = {key: value.value for key, value in LEGACY_CORRECTION_MODE_MAP.items()}
CANONICAL_STEP3_MODES = frozenset(mode.value for mode in CorrectionMode)


def normalize_step3_mode(value: str) -> str:
    return normalize_correction_mode(value).value
