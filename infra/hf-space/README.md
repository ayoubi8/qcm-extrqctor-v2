# Hugging Face Spaces Worker

Role: long-running Python worker process.

Responsibilities:

- poll durable task queue.
- run PDF/OCR/QCM/correction/similarity/automation tasks.
- write artifacts to private Supabase Storage.
- emit terminal and task events.

Free CPU Basic expectations:

- startup can be cold after sleep.
- worker must tolerate restart and reclaim tasks by lease.
- temporary disk is not durable.
- large intermediate files must move to private storage.
