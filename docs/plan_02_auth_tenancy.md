# Plan 02 Auth And Tenancy Notes

Status: implemented as dependency-light contracts and boundaries.

Implemented:

- Provider-free auth domain types: roles, profile statuses, user context, worker context.
- Shared DTOs for login/register/session/profile/preferences/model preferences/usage/audit/account deletion.
- Application ownership guards for active-profile, admin, owner, and project owner checks.
- Auth service ports for Supabase-backed sign-in, sign-up, token verification, approval, preferences, audit, and deletion request workflows.
- Supabase adapter boundary with configuration validation and service-context guard.
- API auth route factory for `/auth/login` and `/auth/register`.
- Worker auth context helper.
- Frontend auth session store, API helper, and approval-aware `AuthGate`.
- Security tests for approval gate, cross-user denial, admin scope, worker scope, and auth contract validation.

Deferred to Plan 03 and later:

- Real `profiles`, preferences, usage, and audit tables.
- Supabase RLS policies and live token verification.
- Full frontend login/register pages and admin panel integration.
- Storage/signed URL authorization.

Verification:

```powershell
python -B tools/verify_foundation.py
python -B -m unittest discover tests
```

Result: both commands passed with 13 unit tests.

Next plan: Plan 03 Database Schema, RLS, And Migrations.
