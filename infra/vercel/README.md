# Vercel Deployment

Role: static frontend and short API flows only.

Allowed work:

- frontend static build.
- auth/profile metadata.
- upload initialization.
- task creation/status.
- signed URL creation.
- health/readiness checks.

Not allowed:

- PDF rendering.
- OCR.
- Step processing.
- AI planning/evaluation.
- long-running worker loops.

Large files must use signed upload/storage flows. Vercel Functions are not used for direct 50 MB PDF bodies.
