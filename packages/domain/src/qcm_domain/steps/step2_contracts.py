"""Domain rules for the visible combined Step 2 product step."""

from qcm_domain.enums import InternalCycleKey, ProductStepKey

COMBINED_STEP2_PRODUCT_STEP = ProductStepKey.STEP2_QCM_EXTRACTION
COMBINED_STEP2_CYCLE_ORDER: tuple[InternalCycleKey, ...] = (
    InternalCycleKey.STEP2_QCM_PAGES,
    InternalCycleKey.STEP2_METADATA,
    InternalCycleKey.STEP2_FORMAT,
    InternalCycleKey.STEP2_FINALIZE,
)


def validate_combined_step2_cycle(cycle: InternalCycleKey | str) -> InternalCycleKey:
    try:
        key = cycle if isinstance(cycle, InternalCycleKey) else InternalCycleKey(cycle)
    except ValueError as exc:
        raise ValueError(f"Unsupported combined Step 2 cycle: {cycle}") from exc
    if key not in COMBINED_STEP2_CYCLE_ORDER:
        raise ValueError(f"Cycle {key.value} does not belong to combined Step 2")
    return key


def cycle_index(cycle: InternalCycleKey | str) -> int:
    key = validate_combined_step2_cycle(cycle)
    return COMBINED_STEP2_CYCLE_ORDER.index(key)


def cycles_from(cycle: InternalCycleKey | str | None = None) -> tuple[InternalCycleKey, ...]:
    if cycle is None:
        return COMBINED_STEP2_CYCLE_ORDER
    return COMBINED_STEP2_CYCLE_ORDER[cycle_index(cycle) :]
