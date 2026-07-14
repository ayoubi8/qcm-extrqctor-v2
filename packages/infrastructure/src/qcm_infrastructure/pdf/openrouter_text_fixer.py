"""LLM-based text repair via OpenRouter.

Replaces IdentityTextQualityFixer with real OCR-error correction powered by an LLM.
Only called when config.text_fixer_enabled is True (Step1Service handles that gate).
"""

from __future__ import annotations

from qcm_infrastructure.pdf.base import TextRepairResult
from qcm_shared.provider_contracts import ModelCallRequest, ModelCallResponse, ProviderKey

try:
    from qcm_infrastructure.llm.openrouter_adapter import OpenRouterAdapter, OpenRouterSettings
except ImportError:  # pragma: no cover
    OpenRouterAdapter = None  # type: ignore[assignment]


class OpenRouterTextFixer:
    """Implements the TextQualityFixer Protocol."""

    def __init__(self, adapter: OpenRouterAdapter | None = None, *, default_model_id: str = "openai/gpt-4o-mini") -> None:
        self.adapter = adapter
        self.default_model_id = default_model_id

    def repair(self, text: str, *, page_number: int, model_id: str | None = None) -> TextRepairResult:
        if self.adapter is None:
            return TextRepairResult(text=text.strip(), changed=text != text.strip())

        model = model_id or self.default_model_id
        prompt = _build_repair_prompt(text, page_number)
        try:
            response = self.adapter.complete_json(
                ModelCallRequest(
                    provider=ProviderKey.OPENROUTER,
                    model_id=model,
                    prompt=prompt,
                    schema_version="text-repair.v1",
                    purpose="step1_text_quality",
                    correlation_id=f"text-repair-page-{page_number}",
                    max_tokens=4000,
                    temperature=0.1,
                )
            )
            repaired = _extract_repaired_text(response)
            changed = repaired != text
            return TextRepairResult(
                text=repaired,
                changed=changed,
                warnings=() if changed else (f"Page {page_number} had no repairs needed",),
                provider="openrouter",
                model_id=model,
            )
        except Exception as exc:
            return TextRepairResult(
                text=text.strip(),
                changed=text != text.strip(),
                warnings=(f"Text repair failed on page {page_number}: {exc}",),
                provider="openrouter",
                model_id=model,
            )


def _build_repair_prompt(text: str, page_number: int) -> str:
    return (
        f"You are an OCR repair assistant. The following text was extracted from page {page_number} of a QCM exam PDF. "
        "Fix common OCR errors (mangled characters, broken columns, merged lines, missing spaces) while preserving "
        "the original meaning and structure. Return ONLY the repaired text, no explanation.\n\n"
        f"Text to repair:\n{text}"
    )


def _extract_repaired_text(response: ModelCallResponse) -> str:
    if response.parsed_json and isinstance(response.parsed_json, dict) and "repaired_text" in response.parsed_json:
        return str(response.parsed_json["repaired_text"]).strip()
    return response.content.strip() if response.content else ""