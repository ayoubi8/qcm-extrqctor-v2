"""Template validation and QCM row formatting for combined Step 2."""

from dataclasses import asdict
from typing import Any

from qcm_domain.templates import default_qcm_template, validate_qcm_template
from qcm_shared.step2_contracts import Step2FormatResult, Step2RunCommand, Step2TemplateValidation


class Step2FormatService:
    def run(self, command: Step2RunCommand, qcms: list[dict[str, Any]]) -> Step2FormatResult:
        if not qcms:
            raise ValueError("Format cycle requires metadata-enriched QCM records")
        template = default_qcm_template()
        template.update(command.config.template_overrides)
        validation_report = validate_qcm_template(template, template_name=command.config.template_name)
        if not validation_report.valid:
            missing = ", ".join(validation_report.missing_required_fields)
            raise ValueError(f"Step 2 template is missing required fields: {missing}")
        formatted = tuple(_map_to_template(qcm, template) for qcm in qcms)
        validation = Step2TemplateValidation(
            template_name=validation_report.template_name,
            valid=validation_report.valid,
            missing_required_fields=validation_report.missing_required_fields,
            warnings=validation_report.warnings,
        )
        warnings = list(validation.warnings)
        if command.config.template_name != "default" and not command.config.template_overrides:
            warnings.append(f"Template '{command.config.template_name}' is not installed locally; default template used")
        return Step2FormatResult(
            template=template,
            formatted_qcms=formatted,
            validation=validation,
            warnings=tuple(dict.fromkeys(warnings)),
        )


def _map_to_template(qcm: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    mapped = dict(template)
    field_map = {
        "Num": ("number", "Num", "id", "num"),
        "Text": ("text", "Text", "question", "questionText"),
        "Correct": ("correction", "Correct", "answer"),
        "categoryName": ("module", "categoryName", "module_detected"),
        "subcategoryName": ("subcategory", "subcategoryName", "legacy_subcategory"),
        "Year": ("year", "Year"),
        "Source": ("source", "Source"),
        "Tag": ("tag", "Tag"),
        "Cas": ("cas", "Cas", "clinical_case"),
    }
    for target, candidates in field_map.items():
        if target not in mapped:
            continue
        for source in candidates:
            value = qcm.get(source)
            if value not in (None, "", []):
                mapped[target] = value
                break
    propositions = qcm.get("propositions") or {}
    for key in ("A", "B", "C", "D", "E"):
        if key in mapped:
            mapped[key] = qcm.get(key) or propositions.get(key) or propositions.get(key.lower()) or mapped[key]
    cas_value = qcm.get("cas") or qcm.get("Cas")
    if cas_value and "Cas" not in mapped:
        mapped["Cas"] = cas_value
    return mapped


def format_result_payload(result: Step2FormatResult) -> dict[str, Any]:
    return {
        "template": result.template,
        "formatted_qcms": list(result.formatted_qcms),
        "validation": asdict(result.validation),
        "warnings": list(result.warnings),
    }
