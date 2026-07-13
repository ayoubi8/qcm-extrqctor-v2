# Plan 04 Storage, Artifacts, File-Size Limits, And Cleanup Notes

Status: implemented as storage/artifact contracts, adapters, services, and verification.

Implemented:

- Private storage key builder using `users/{user_id}/projects/{project_id}/...` paths.
- 50 MB source-file validation with `file_size_limit` provider-limit signaling.
- Complete artifact registry coverage for every shared artifact type.
- Shared DTOs for upload init, artifact writes, signed URLs, cleanup candidates/reports, and legacy artifact manifests.
- Application artifact service for checksum validation, object writes, metadata handoff, signed URL ownership checks, audit event creation, and cleanup execution.
- In-memory storage adapter for tests and Supabase Storage adapter boundary for private buckets.
- API artifact route factory for upload initialization and signed URL issuance.
- Worker cleanup helpers for retention policy selection.
- Plan 04 verifier and unit tests for registry coverage, private keys, size cap, checksum mismatch, signed URL ownership, audit, and cleanup.

Deferred to later plans:

- Live Supabase Storage bucket creation and storage policy tests.
- Repository implementations that persist artifact metadata in Postgres.
- Real signed URL API auth dependency wiring.
- Legacy folder scan/copy jobs against real storage and local output directories.
- Account-deletion storage cleanup execution against the provider.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B tools/verify_migrations.py
python -B tools/verify_storage.py
python -B -m unittest discover tests
```

Result: all commands passed.

Next plan: Plan 05 Backend Domain, API, And Provider Foundation.
