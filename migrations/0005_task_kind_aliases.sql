-- Phase B fix: align the public.task_kind enum with the application task-kind constants.
-- The migrations 0002/0003 enum was designed for granular Step 2 cycles, but the
-- application uses a single visible "step2_orchestrate" kind and the "manual_autorun"
-- / "ai_autorun" spellings. Add those as aliases without removing the granular ones.
--
-- ALTER TYPE ... ADD VALUE cannot run inside a transaction block on older Postgres;
-- with IF NOT EXISTS PG12+ tolerates it. Run these statements individually (autocommit).

alter type public.task_kind add value if not exists 'step2_orchestrate';
alter type public.task_kind add value if not exists 'manual_autorun';
alter type public.task_kind add value if not exists 'ai_autorun';

comment on type public.task_kind is
  'Task kinds used by the worker. step2_orchestrate/manual_autorun/ai_autorun are the application-visible single-task kinds; the granular step2_* values are reserved for future cycle-level tasks.';