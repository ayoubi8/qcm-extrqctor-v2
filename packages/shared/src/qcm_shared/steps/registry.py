"""Canonical product-step registry for the future visible workflow."""

from dataclasses import dataclass

from qcm_domain.enums import ProductStepKey


@dataclass(frozen=True, slots=True)
class ProductStepDefinition:
    key: ProductStepKey
    order: int
    label: str
    task_kinds: tuple[str, ...]


PRODUCT_STEP_REGISTRY: tuple[ProductStepDefinition, ...] = (
    ProductStepDefinition(ProductStepKey.STEP1_TEXT_EXTRACTION, 1, "Text Extraction", ("step1_extract",)),
    ProductStepDefinition(
        ProductStepKey.STEP2_QCM_EXTRACTION,
        2,
        "QCM Extraction",
        ("step2_orchestrate",),
    ),
    ProductStepDefinition(ProductStepKey.STEP3_CORRECTION, 3, "Correction", ("step3_correction",)),
    ProductStepDefinition(
        ProductStepKey.STEP4_SIMILARITY_MATCH,
        4,
        "Similarity Match",
        ("step4_similarity_match",),
    ),
)
