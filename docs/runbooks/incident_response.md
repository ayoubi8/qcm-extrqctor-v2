# Incident Response Runbook

Severity examples:

- P0: cross-user data exposure, storage policy failure, leaked secret.
- P1: task queue cannot process work, uploads rejected globally, provider outage without fallback.
- P2: degraded terminal replay, worker cold-start delays, non-critical artifact preview issue.

First actions:

1. Freeze writes when data integrity is at risk.
2. Preserve logs and audit events.
3. Rotate affected secrets.
4. Notify impacted users with safe detail only.
5. File a post-incident note with root cause and prevention.
