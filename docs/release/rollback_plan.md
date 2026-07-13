# Rollback Plan

Immediate rollback:

- disable new task creation and automation starts.
- keep Results/History read-only.
- stop workers after current leases expire or are cancelled.
- restore previous frontend/API deployment.

Data rollback:

- do not delete failed-run artifacts automatically.
- preserve audit and terminal events.
- quarantine failed legacy imports.
- restore database/storage from staging-validated backup when required.
