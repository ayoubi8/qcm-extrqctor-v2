# Provider Limits Snapshot

Reviewed: 2026-07-13.

Sources:

- Vercel Functions limits: https://vercel.com/docs/functions/limitations
- Supabase pricing and free quotas: https://supabase.com/pricing
- Hugging Face Spaces overview: https://huggingface.co/docs/hub/spaces-overview
- Hugging Face Spaces hardware: https://huggingface.co/docs/hub/spaces-gpus

Deployment assumptions:

- Vercel is used for static frontend and short API flows. Vercel request body limits mean direct PDF upload bodies are not accepted by serverless functions.
- Supabase is the authority for Postgres, Auth, RLS, private Storage, and Realtime.
- Hugging Face Spaces runs the Python worker. Free CPU hardware can sleep, so durable task leases and retry behavior are required.

Current guardrails captured in code:

- QCM source upload cap: 52,428,800 bytes.
- Vercel request body budget: 4,500,000 bytes.
- Supabase storage free-tier budget: 1 GB.
- Supabase database free-tier budget: 500 MB.
- Hugging Face CPU Basic memory budget: 16 GB.

Before production launch, re-open the sources above and update this file. Provider free-tier limits change, and this snapshot is not a contract.
