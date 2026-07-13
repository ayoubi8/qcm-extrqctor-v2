"""Final QCM template validation and default schema rules."""

from dataclasses import dataclass
from typing import Any

DEFAULT_QCM_TEMPLATE: dict[str, Any] = {
    "Num": 0,
    "Text": "",
    "A": "",
    "B": "",
    "C": "",
    "D": "",
    "E": "",
    "Correct": "",
    "Year": "",
    "categoryName": "",
    "subcategoryName": "",
    "Source": "",
    "Tag": [],
    "Cas": "",
}

REQUIRED_TEMPLATE_FIELDS = ("Num", "Text")
RECOMMENDED_TEMPLATE_FIELDS = ("A", "B", "C", "D", "E")


@dataclass(frozen=True, slots=True)
class TemplateValidationReport:
    valid: bool
    template_name: str
    missing_required_fields: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def default_qcm_template() -> dict[str, Any]:
    return dict(DEFAULT_QCM_TEMPLATE)


def validate_qcm_template(template: dict[str, Any], *, template_name: str = "default") -> TemplateValidationReport:
    missing = tuple(field for field in REQUIRED_TEMPLATE_FIELDS if field not in template or template[field] is None)
    warnings: list[str] = []
    missing_recommended = [field for field in RECOMMENDED_TEMPLATE_FIELDS if field not in template]
    if missing_recommended:
        warnings.append(f"Template is missing recommended proposition fields: {', '.join(missing_recommended)}")
    return TemplateValidationReport(
        valid=not missing,
        template_name=template_name,
        missing_required_fields=missing,
        warnings=tuple(warnings),
    )
