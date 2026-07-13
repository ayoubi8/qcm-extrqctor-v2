# Staged Rollout Plan

1. Local verification gate.
2. Staging deployment with synthetic fixtures.
3. Live RLS/storage/security checks.
4. Backup/restore drill.
5. Limited admin-only pilot.
6. Read-only legacy import pilot.
7. General availability after final acceptance.

Stop conditions:

- cross-user data access.
- artifact overwrite or history loss.
- provider limit errors without graceful degradation.
- backup restore cannot recover a project.
