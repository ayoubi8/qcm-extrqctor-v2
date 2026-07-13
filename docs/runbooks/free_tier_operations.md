# Free-Tier Operations Runbook

Budgets:

- 50 MB source file cap before heavy processing.
- avoid routing large file bodies through Vercel Functions.
- keep worker temp files disposable.
- monitor storage growth and cleanup candidates.
- degrade gracefully when provider limits are reached.

Upgrade triggers:

- Supabase storage or database budget warning.
- repeated worker sleep/restart delays.
- provider rate-limit failures across fallback models.
- terminal/realtime volume exceeds budget.

Graceful degradation:

- allow read-only Results/History.
- pause AI Auto Run and Manual Auto Run starts.
- keep artifact downloads through signed URLs.
- surface provider-limit warnings in terminal events.
