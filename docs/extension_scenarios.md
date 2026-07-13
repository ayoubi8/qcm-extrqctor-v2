# Extension Scenarios

## LLM Provider

Add a provider by implementing the application LLM port in infrastructure and registering a provider key. OpenRouter is the only initial provider.

## OCR Provider

Add an OCR adapter behind the OCR port. Step handlers depend on the port, not the OCR SDK.

## Pipeline Step

Add a product step or internal cycle by updating the shared step registry, task kind list, terminal event behavior, and artifact contracts.

## Correction Mode

Future Step 3 uses canonical modes only:

- `page_detection`
- `vision`
- `auto_detection`

Legacy aliases are mapped at API/import boundaries, not inside domain execution.

## Artifact Viewer

Add an artifact viewer by registering the artifact type, schema version, content type, and retention policy. The viewer reads signed URLs only after ownership checks.

## Metadata Field

Add query-critical metadata as first-class schema or database fields. Flexible evidence can live in JSON payloads when it is not required for authorization, status, or primary queries.
