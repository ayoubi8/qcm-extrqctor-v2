"""Metadata, legacy subcategory, and Cas Clinique enrichment for combined Step 2."""

from dataclasses import asdict
import re
from typing import Any

from qcm_shared.step2_contracts import (
    STEP2_METADATA_PROMPT_ID,
    Step2ClinicalGroup,
    Step2MetadataProvenance,
    Step2MetadataResult,
    Step2RunCommand,
)

_CASE_RE = re.compile(r"\b(CAS\s+CLINIQUE(?:\s*(?:N[°o]\s*)?\d+)?)\b\s*:?\s*(.*)", re.IGNORECASE)
_QUESTION_RE = re.compile(r"^\s*(?:Q(?:uestion)?\s*)?\d+[\).\:-]")
_PROP_RE = re.compile(r"^\s*[A-Ea-e][\)\].:-]\s+")


class Step2MetadataService:
    def run(self, command: Step2RunCommand, qcms: list[dict[str, Any]]) -> Step2MetadataResult:
        if not qcms:
            raise ValueError("Metadata cycle requires QCM records")
        page_cases = _detect_page_cases(command)
        enriched: list[dict[str, Any]] = []
        provenance: list[Step2MetadataProvenance] = []
        grouped_uids: dict[str, list[str]] = {}
        grouped_pages: dict[str, set[int]] = {}
        warnings: list[str] = []

        for qcm in qcms:
            item = dict(qcm)
            item_provenance = _apply_metadata_defaults(item, command)
            provenance.extend(item_provenance)
            page_number = int(item.get("page") or item.get("source_page") or 0)
            case = page_cases.get(page_number)
            if case:
                item["cas"] = f"{case['label']}\r\n{case['narrative']}".strip()
                provenance.append(
                    Step2MetadataProvenance(
                        field_name="cas",
                        strategy="page_case_detection",
                        source=STEP2_METADATA_PROMPT_ID,
                        value=case["label"],
                        qcm_uid=item.get("uid"),
                    )
                )
                grouped_uids.setdefault(case["group_id"], []).append(item.get("uid", ""))
                grouped_pages.setdefault(case["group_id"], set()).add(page_number)
            _apply_legacy_subcategory_policy(item, command, provenance)
            _refresh_tags(item)
            enriched.append(item)

        clinical_groups = tuple(
            Step2ClinicalGroup(
                group_id=group_id,
                label=page_cases[next(iter(pages))]["label"],
                narrative=page_cases[next(iter(pages))]["narrative"],
                qcm_uids=tuple(uid for uid in grouped_uids[group_id] if uid),
                page_numbers=tuple(sorted(pages)),
            )
            for group_id, pages in grouped_pages.items()
        )
        if not provenance:
            warnings.append("Metadata cycle preserved extracted fields only")
        if command.config.legacy_subcategory_policy == "drop":
            warnings.append("Legacy subcategory fields were dropped by configuration")
        return Step2MetadataResult(
            qcms=tuple(enriched),
            provenance=tuple(provenance),
            clinical_groups=clinical_groups,
            warnings=tuple(dict.fromkeys(warnings)),
        )


def _detect_page_cases(command: Step2RunCommand) -> dict[int, dict[str, str]]:
    page_cases: dict[int, dict[str, str]] = {}
    active: dict[str, str] | None = None
    case_index = 0
    for page in sorted(command.pages, key=lambda item: item.page_number):
        found = _extract_case_from_text(page.text)
        if found:
            case_index += 1
            active = {
                "group_id": f"case-{case_index}",
                "label": found["label"],
                "narrative": found["narrative"],
            }
        if active:
            page_cases[page.page_number] = dict(active)
    return page_cases


def _extract_case_from_text(text: str) -> dict[str, str] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        match = _CASE_RE.search(line)
        if not match:
            continue
        narrative_parts = [match.group(2).strip()] if match.group(2).strip() else []
        for following in lines[index + 1 :]:
            if _QUESTION_RE.match(following) or _PROP_RE.match(following) or _CASE_RE.search(following):
                break
            narrative_parts.append(following)
        return {
            "label": match.group(1).upper().replace("  ", " "),
            "narrative": " ".join(part for part in narrative_parts if part).strip(),
        }
    return None


def _apply_metadata_defaults(
    item: dict[str, Any],
    command: Step2RunCommand,
) -> list[Step2MetadataProvenance]:
    field_map = {
        "year": "year",
        "source": "source",
        "category": "module_detected",
        "subcategory": "subcategory",
    }
    provenance: list[Step2MetadataProvenance] = []
    for config_field, qcm_field in field_map.items():
        default = command.config.metadata_defaults.get(config_field)
        strategy = command.config.metadata_strategies.get(config_field, "manual_default" if default else "preserve")
        if default and not item.get(qcm_field):
            item[qcm_field] = default
            provenance.append(
                Step2MetadataProvenance(
                    field_name=qcm_field,
                    strategy=strategy,
                    source="config_default",
                    value=default,
                    qcm_uid=item.get("uid"),
                )
            )
        elif item.get(qcm_field):
            provenance.append(
                Step2MetadataProvenance(
                    field_name=qcm_field,
                    strategy="preserve_extracted",
                    source="qcm_record",
                    value=str(item[qcm_field]),
                    qcm_uid=item.get("uid"),
                )
            )
    return provenance


def _apply_legacy_subcategory_policy(
    item: dict[str, Any],
    command: Step2RunCommand,
    provenance: list[Step2MetadataProvenance],
) -> None:
    subcategory = item.get("subcategory")
    if not subcategory:
        return
    policy = command.config.legacy_subcategory_policy
    if policy == "drop":
        item.pop("subcategory", None)
        item.pop("legacy_subcategory", None)
        return
    item["legacy_subcategory"] = subcategory
    if policy == "preserve_internal":
        item.pop("subcategory", None)
    provenance.append(
        Step2MetadataProvenance(
            field_name="legacy_subcategory",
            strategy=policy,
            source="compatibility_metadata",
            value=str(subcategory),
            qcm_uid=item.get("uid"),
        )
    )


def _refresh_tags(item: dict[str, Any]) -> None:
    tags = [value for value in (item.get("source"), item.get("year")) if value]
    if tags:
        item["tag"] = tags


def metadata_result_payload(result: Step2MetadataResult) -> dict[str, Any]:
    return {
        "qcms": list(result.qcms),
        "provenance": [asdict(item) for item in result.provenance],
        "clinical_groups": [asdict(item) for item in result.clinical_groups],
        "warnings": list(result.warnings),
    }
