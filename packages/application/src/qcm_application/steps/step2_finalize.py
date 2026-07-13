"""Final JSON and XLSX artifact payload builder for combined Step 2."""

import json
from typing import Any

from qcm_shared.step2_contracts import Step2FinalizeResult, Step2RunCommand


class Step2FinalizeService:
    def run(self, command: Step2RunCommand, formatted_qcms: list[dict[str, Any]]) -> Step2FinalizeResult:
        if not formatted_qcms:
            raise ValueError("Finalize cycle requires formatted QCM records")
        warnings: list[str] = []
        if any(not qcm.get("Text") for qcm in formatted_qcms):
            warnings.append("One or more final QCM rows have empty Text fields")
        final_json = json.dumps(formatted_qcms, sort_keys=True, separators=(",", ":")).encode("utf-8")
        final_xlsx = _xlsx_placeholder_bytes(formatted_qcms) if command.config.output_format == "json+xlsx" else None
        return Step2FinalizeResult(
            final_qcms=tuple(formatted_qcms),
            final_json_content=final_json,
            final_xlsx_content=final_xlsx,
            warnings=tuple(warnings),
        )


def _xlsx_placeholder_bytes(qcms: list[dict[str, Any]]) -> bytes:
    columns = ["Num", "Text", "A", "B", "C", "D", "E", "Correct", "Year", "categoryName", "subcategoryName", "Source", "Cas"]
    rows = [",".join(columns)]
    for qcm in qcms:
        values = []
        for column in columns:
            value = qcm.get(column, "")
            if isinstance(value, list):
                value = "|".join(str(item) for item in value)
            escaped = str(value).replace('"', '""')
            values.append(f'"{escaped}"')
        rows.append(",".join(values))
    return ("\n".join(rows) + "\n").encode("utf-8")
