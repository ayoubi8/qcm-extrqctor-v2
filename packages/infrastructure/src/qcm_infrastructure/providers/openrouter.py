"""OpenRouter adapter placeholder.

The concrete SDK integration is implemented after provider and task contracts are wired.
"""


class OpenRouterProvider:
    provider_key = "openrouter"

    def complete_json(self, *, model_id: str, prompt: str, schema_version: str) -> dict:
        raise NotImplementedError("OpenRouter calls are implemented in a later plan")
