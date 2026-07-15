"""LLM-based AI Auto Run document map planner.

Calls OpenRouter with the planner prompt + page texts, parses the JSON response
into a document map. Falls back to the deterministic keyword matcher if the
LLM call fails or returns invalid JSON.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from qcm_domain.ai_autorun import AiDocumentMap, AiDocumentMapPage
from qcm_shared.ai_autorun_contracts import AiAutoRunPageInput

logger = logging.getLogger(__name__)

_PLANNER_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "ai_autorun" / "planner.v1.md"

_PLANNER_SYSTEM_PROMPT = """You are an AI document planner for a QCM (multiple-choice question) exam extraction system.
Analyze the following pages from an exam PDF and classify each page.

For each page, return:
- "role": one of "question", "correction", or "context"
  - "question": contains QCM questions with answer choices
  - "correction": contains answer keys or corrections
  - "context": contains intro text, case studies, or non-question content
- "confidence": float between 0.0 and 1.0
- "summary": brief one-sentence description of the page content

Return ONLY a JSON object with this exact schema, no markdown or explanation:
{{
  "pages": [
    {{"page_number": 1, "role": "question", "confidence": 0.9, "summary": "Contains 5 QCM questions about anatomy"}}
  ]
}}
"""


def _load_planner_prompt() -> str:
    """Load the planner prompt template, or fall back to the inline system prompt."""
    try:
        return _PLANNER_SYSTEM_PROMPT + "\n\n" + _PLANNER_PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return _PLANNER_SYSTEM_PROMPT


def plan_with_llm(pages: tuple[AiAutoRunPageInput, ...], adapter) -> AiDocumentMap | None:
    """Call OpenRouter with page texts and parse the document map response.

    Returns None if the LLM call fails or returns invalid JSON (caller falls back
    to the deterministic planner).
    """
    if adapter is None or not pages:
        return None

    prompt = _load_planner_prompt()
    pages_text = "\n\n".join(
        f"--- Page {page.page_number} ---\n{page.text[:3000]}"
        for page in pages
    )
    full_prompt = prompt + "\n\nPage texts:\n" + pages_text

    try:
        from qcm_shared.provider_contracts import ModelCallRequest, ProviderKey
        response = adapter.complete_json(
            ModelCallRequest(
                provider=ProviderKey.OPENROUTER,
                model_id="openai/gpt-4o-mini",
                prompt=full_prompt,
                schema_version="ai-autorun-planner.v1",
                purpose="ai_autorun_planner",
                correlation_id="ai-planner",
                max_tokens=4000,
                temperature=0.1,
            )
        )
        return _parse_llm_response(response.parsed_json, response.content, pages)
    except Exception as exc:
        logger.warning("AI Auto Run LLM planner failed, falling back to deterministic: %s", exc)
        return None


def _parse_llm_response(parsed_json: dict[str, Any] | None, raw_content: str, pages: tuple[AiAutoRunPageInput, ...]) -> AiDocumentMap | None:
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
        return None

    raw_pages = data.get("pages") or []
    if not isinstance(raw_pages, list):
        return None

    mapped: list[AiDocumentMapPage] = []
    page_by_number = {p.page_number: p for p in pages}

    for rp in raw_pages:
        if not isinstance(rp, dict):
            continue
        page_number = rp.get("page_number")
        if page_number is None:
            continue
        page_number = int(page_number)
        role = str(rp.get("role", "context")).lower()
        if role not in ("question", "correction", "context"):
            role = "context"
        confidence = float(rp.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
        summary = str(rp.get("summary", f"Page {page_number} classified as {role}"))

        mapped.append(
            AiDocumentMapPage(
                page_number=page_number,
                role=role,
                confidence=confidence,
                evidence_summary=summary,
            )
        )

    # Ensure all input pages are represented (fill missing ones as "context")
    existing_numbers = {m.page_number for m in mapped}
    for page in pages:
        if page.page_number not in existing_numbers:
            mapped.append(
                AiDocumentMapPage(
                    page_number=page.page_number,
                    role="context",
                    confidence=0.5,
                    evidence_summary=f"Page {page.page_number} not classified by LLM",
                )
            )

    return AiDocumentMap(tuple(mapped))