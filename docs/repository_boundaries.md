# Repository Boundaries

Plan 01 establishes boundaries that later plans must preserve.

## Dependency Direction

Allowed direction:

```text
apps/* -> packages/application -> packages/domain
apps/* -> packages/shared
packages/application -> packages/shared
packages/infrastructure -> packages/application, packages/domain, packages/shared
```

Forbidden direction:

- `packages/domain` importing app, infrastructure, or provider SDK code.
- `packages/shared` importing API, worker, web, or infrastructure adapters.
- `packages/application` importing concrete database, storage, OCR, LLM, or web code.
- `apps/web` becoming the authority for execution configuration or ownership.

## Ownership Rule

Every project-scoped command and DTO introduced by later plans must carry or resolve:

- `user_id`
- `project_id`
- `correlation_id`

Frontend filters are never authorization. API checks, database RLS, storage metadata, and signed URL issuance all enforce ownership.

## Extension Rule

New providers, OCR engines, pipeline steps, correction modes, artifact viewers, and metadata fields are added by registering contracts and adapters. Domain behavior must not depend on a concrete provider SDK.
