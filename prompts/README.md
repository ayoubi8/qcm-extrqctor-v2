# Prompts

Prompt templates are versioned source artifacts.

Rules:

- Store prompts by provider-independent purpose, not provider SDK.
- Record schema version and expected structured output.
- Do not store raw private model reasoning in client-visible artifacts.
- Prompt/response bodies, when persisted later, are private artifacts with audited admin access.
