# Deployment Runbook

Order:

1. Create Supabase project.
2. Apply migrations in order.
3. Create private `qcm-artifacts-private` bucket.
4. Apply storage policies.
5. Configure server secrets.
6. Deploy worker to Hugging Face Spaces.
7. Deploy frontend and short API flows to Vercel.
8. Run health checks: `/health`, `/ready`, `/metrics`.
9. Create a small project and verify terminal replay.

Rollback:

- Disable new task creation routes first.
- Keep Results/History read-only.
- Stop workers after active leases expire or are cancelled.
- Restore previous Vercel deployment if frontend/API routing regresses.
