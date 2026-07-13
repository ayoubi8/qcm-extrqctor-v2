# Migration Acceptance

Rules:

- legacy import is user initiated or admin assigned.
- ambiguous artifacts become read-only quarantined warnings.
- checksums are required before import.
- timestamps, subcategories, step history, source paths, and artifacts are preserved where evidence exists.
- private fixture files are not committed without explicit approval.

Rollback:

- legacy mode stays read-only until release is accepted.
- failed imports do not delete source legacy data.
- imported artifacts can be hidden without deleting historical evidence.
