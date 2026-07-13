# Deployment Runbook

Order:

1. Create Supabase project.
2. Apply migrations in order.
3. Create private `qcm-artifacts-private` bucket.
4. Apply storage policies.
5. Configure server secrets.
6. Deploy the API to a Hugging Face Space with SDK `Gradio`, app file `app.py`, and free CPU hardware.
7. Set `VITE_API_BASE_URL` in Vercel to the Hugging Face Space URL.
8. Deploy frontend to Vercel.
9. Run health checks: `/health`, `/ready`, `/metrics`.
10. Create a small project and verify terminal replay.

Rollback:

- Disable new task creation routes first.
- Keep Results/History read-only.
- Stop workers after active leases expire or are cancelled.
- Restore previous Vercel deployment if frontend/API routing regresses.
