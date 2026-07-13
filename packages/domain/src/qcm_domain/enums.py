"""Domain enums that are independent of storage, API, and provider choices."""

from enum import StrEnum


class ProductStepKey(StrEnum):
    STEP1_TEXT_EXTRACTION = "step1_text_extraction"
    STEP2_QCM_EXTRACTION = "step2_qcm_extraction"
    STEP3_CORRECTION = "step3_correction"
    STEP4_SIMILARITY_MATCH = "step4_similarity_match"


class InternalCycleKey(StrEnum):
    STEP1_DETECTION = "step1_detection"
    STEP1_TEXT_QUALITY = "step1_text_quality"
    STEP2_QCM_PAGES = "step2_qcm_pages"
    STEP2_METADATA = "step2_metadata"
    STEP2_FORMAT = "step2_format"
    STEP2_FINALIZE = "step2_finalize"
    STEP3_PAGE_DETECTION = "step3_page_detection"
    STEP3_VISION = "step3_vision"
    STEP3_AUTO_DETECTION = "step3_auto_detection"
    STEP4_MATCH = "step4_match"
