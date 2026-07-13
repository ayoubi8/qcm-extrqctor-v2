# Hugging Face Spaces API

Role: free-tier Docker Space for the FastAPI backend.

Responsibilities:

- serve `/health`, `/ready`, `/auth/login`, `/auth/register`, and short-running API requests.
- authenticate with Supabase Auth.
- create/read owner-scoped profile rows through the Supabase service role.
- allow the Vercel frontend through `QCM_CORS_ALLOW_ORIGINS`.

Free CPU Basic expectations:

- startup can be cold after sleep.
- temporary disk is not durable.
- large intermediate files must move to private storage.
