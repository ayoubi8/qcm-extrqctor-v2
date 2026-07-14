"""LLM-backed QCM page extractor for Step 2.

Calls OpenRouter with each page's text and parses QCM questions/propositions
from the LLM's JSON response. Falls back to the rule-based extractor on error.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from qcm_application.steps.step2_pages import PageExtractionDraft, PageQcmExtractor, RuleBasedPageQcmExtractor
from qcm_shared.step2_contracts import Step2PageTaskInput
from qcm_shared.provider_contracts import ModelCallRequest, ProviderKey

logger = logging.getLogger(__name__)

_QCM_EXTRACTION_PROMPT = """You are a QCM (multiple-choice question) extraction assistant.
Extract all multiple-choice questions from the following page text.
For each question, return the question number, the question text, and all propositions (answer choices) with their letter (A-E).

Return ONLY a JSON object with this exact schema, no explanation:
{{
  "questions": [
    {{
      "number": 1,
      "text": "The question text",
      "propositions": [
        {{"letter": "A", "text": "First choice"}},
        {{"letter": "B", "text": "Second choice"}}
      ]
    }}
  ]
}}

If no QCM questions are found, return: {{"questions": []}}

Page text:
{page_text}"""


class LlmPageQcmExtractor:
    """Implements the PageQcmExtractor Protocol using OpenRouter."""

    def __init__(self, adapter, *, model_id: str = "openai/gpt-4o-mini", fallback: PageQcmExtractor | None = None) -> None:
        self.adapter = adapter
        self.model_id = model_id
        self.fallback = fallback or RuleBasedPageQcmExtractor()

    def extract(self, page_input: Step2PageTaskInput) -> PageExtractionDraft:
        if self.adapter is None:
            return self.fallback.extract(page_input)

        prompt = _QCM_EXTRACTION_PROMPT.format(page_text=page_input.current_page_text)
        try:
            response = self.adapter.complete_json(
                ModelCallRequest(
                    provider=ProviderKey.OPENROUTER,
                    model_id=self.model_id,
                    prompt=prompt,
                    schema_version="step2.page_qcm_extraction.v1",
                    purpose="step2_qcm_extraction",
                    correlation_id=f"step2-page-{page_input.page_number}",
                    max_tokens=4000,
                    temperature=0.1,
                )
            )
            return self._parse_response(response.parsed_json, response.content, page_input.page_number)
        except Exception as exc:
            logger.warning("LLM QCM extraction failed for page %s, falling back to rules: %s", page_input.page_number, exc)
            draft = self.fallback.extract(page_input)
            return PageExtractionDraft(
                qcms=draft.qcms,
                orphan_propositions=draft.orphan_propositions,
                warnings=(*draft.warnings, f"LLM extraction failed, used rule-based fallback: {exc}"),
            )

    def _parse_response(self, parsed_json: dict[str, Any] | None, raw_content: str, page_number: int) -> PageExtractionDraft:
        data = parsed_json
        if data is None and raw_content:
            try:
                import re
                match = re.search(r'\{.*\}', raw_content, flags=re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
            except Exception:
                data = None

        if not data or not isinstance(data, dict):
            return PageExtractionDraft(qcms=(), orphan_propositions={}, warnings=("LLM returned no parseable JSON",))

        questions = data.get("questions") or []
        if not isinstance(questions, list):
            questions = []

        qcms: list[dict[str, Any]] = []
        warnings: list[str] = []

        for q in questions:
            if not isinstance(q, dict):
                continue
            number = q.get("number")
            text = q.get("text", "")
            props_raw = q.get("propositions") or []
            propositions: dict[str, str] = {}
            for p in props_raw:
                if isinstance(p, dict):
                    letter = str(p.get("letter", "")).upper()
                    ptext = p.get("text", "")
                    if letter and ptext:
                        propositions[letter] = ptext
                elif isinstance(p, str) and len(p) > 1:
                    letter = p[0].upper()
                    propositions[letter] = p[1:].strip(").:- ")

            if number is not None and text:
                qcms.append({
                    "page": page_number,
                    "number": int(number),
                    "text": str(text),
                    "propositions": propositions,
                })

        if not qcms:
            warnings.append(f"No QCM questions extracted from page {page_number} via LLM")

        return PageExtractionDraft(
            qcms=tuple(qcms),
            orphan_propositions={},
            warnings=tuple(warnings),
        )