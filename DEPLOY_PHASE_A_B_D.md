# Phase A + B + D — Live Verification + Deploy Instructions

Status: **Phases A, B, D implemented and live-verified against your Supabase.**
Pending one manual action (migration `0005`) and VPS credentials before I wire the VPS directly.

---

## ✅ Confirmed working (live, against your Supabase project)

1. **Repos live tests pass** (`tests/test_repositories_live.py`): projects create/get/list, pipeline_runs ensure/list, tasks create/list + claim-via-RPC moves to `running`, terminal_events append + cursor replay — with cascade cleanup verified (no leftovers).
2. **Worker live test passes** (`tests/test_worker_live.py`): created a `step1_extract` task on the queue → ran `WorkerRunner.run_once()` → task moved to **`completed`** end-to-end.
3. **Local no-env suite**: 91 tests pass (+all `verify_*.py` scripts green).
4. **Phase A protected-routes test** correctly skips on the live path; its assertions (`user_id` derived from token, client-supplied `user_id` ignored, 401/403/404) pass on the in-memory path.

---

## ⚠️ One manual action needed (DB-level access)

`ALTER TYPE` cannot run via PostgREST from the VPS (the service-role JWT only does REST, not DDL). **Run `migrations/0005_task_kind_aliases.sql` once in the Supabase Dashboard SQL editor:**

```sql
alter type public.task_kind add value if not exists 'step2_orchestrate';
alter type public.task_kind add value if not exists 'manual_autorun';
alter type public.task_kind add value if not exists 'ai_autorun';
```

Until then, Step 2 / Manual Auto Run / AI Auto Run tasks cannot be persisted (insert hits the enum). Step 1/3/4 already work. I can't run this myself without a separate **Supabase postgres connection password** (from Project Settings → Database) — only VPS-SSH won't reach it.

---

## 🖥️ On the VPS (Azure Ubuntu) — what's needed once you give access

Environment file `/etc/qcm-extractor-api.env` (chmod 600) must contain:

```env
SUPABASE_URL=https://rrirgkkawlnyigfaevja.supabase.co
SUPABASE_ANON_KEY=<anon>
SUPABASE_SERVICE_ROLE_KEY=<service-role>
OPENROUTER_API_KEY=<openrouter-key>
QCM_APP_ENV=production
QCM_DEPLOY_TARGET=vps-api
QCM_CORS_ALLOW_ORIGINS=https://20.5.176.133.sslip.io
QCM_MAX_SOURCE_FILE_BYTES=52428800
QCM_LOG_LEVEL=INFO
PORT=8000
QCM_WORKER_ID=azure-worker-1
```

I'll do:

```bash
cd /opt/qcm-extractor-api/current
sudo -u qcm git pull origin main
sudo bash infra/vps/deploy_ubuntu.sh   # installs deps
# add the qcm-extractor-worker systemd unit (from runbook)
sudo systemctl daemon-reload
sudo systemctl restart qcm-extractor-api
sudo systemctl enable --now qcm-extractor-worker
curl http://127.0.0.1:8000/health
# verify a task moves end-to-end on the live queue
```

The `qcm-extractor-worker.service` unit (already in `docs/runbooks/vps_ubuntu_backend.md`):

```ini
[Unit]
Description=QCM Extractor Worker
After=network-online.target qcm-extractor-api.service
Wants=network-online.target

[Service]
Type=simple
User=qcm
WorkingDirectory=/opt/qcm-extractor-api/current
EnvironmentFile=/etc/qcm-extractor-api.env
ExecStart=/opt/qcm-extractor-api/current/.venv/bin/python -m qcm_worker.main
Restart=always
RestartSec=5
StandardOutput=append:/var/log/qcm-extractor/worker.log
StandardError=append:/var/log/qcm-extractor/worker.log

[Install]
WantedBy=multi-user.target
```

After this:
- Projects / runs / tasks **persist** (durable, no more reset on restart).
- The worker **executes** Step 1 / Step 3 / Step 4 (and Step 2 + Auto Runs once 0005 is applied).
- The fabricated `demo-run` behaviour is gone; `/projects/{id}/snapshot` returns real rows or 404.

---

## 🔐 What I need from you (paste when ready)

You chose: **paste IP + user + password here**. Send:

1. VPS IP address
2. Username (e.g. `azureuser`)
3. Password
4. Yes/no — have you run the **3 `ALTER TYPE` lines** in Supabase Studio?
5. Yes/no — is the repo on the VPS at `/opt/qcm-extractor-api/current`?

**Security reminders after we're done:**
- Rotate the VPS user password (it will be in chat history).
- Rotate the Supabase anon/service-role keys if you've pasted them anywhere.
- I will not echo secrets back in command output and will not write secrets into the repo (they live in `/etc/qcm-extractor-api.env` with `chmod 600`, never committed).

---

## ⏭️ What's still not done (next phases)

- **C — Storage**: signed URLs still return `""`; uploads init but downloads don't.
- **E — Real LLM/PDF/OCR**: handlers use `Fake*` adapters and `"configured-by-admin"` model id; Step 2/3/4 expect inputs inline rather than fetching upstream artifacts.
- **F — Manual/AI Auto Run actually running child tasks**: handlers only *plan* child tasks, they don't enqueue + run them.

Those are independently verifiable; Phase B+D give you durable state + a live worker the moment we wire the VPS.

---

## Files changed in this session

- **Backend (Phase A)**: `security.py` (new), `main.py`, `routes/*.py` (auth dependency on all protected routes), `routes/auth.py` (better error codes), `runtime.py` (supabase-env-driven binding).
- **Backend (Phase B)**: `db/postgrest.py` (new), `db/memory.py` (new), `db/repositories.py` (concrete SupabaseProjectRunTaskTerminal repos), `RuntimeProjectService.runtime.py` (real repos).
- **Backend (Phase D)**: `worker/main.py` (runnable loop), `migrations/0005_task_kind_aliases.sql` (new), runbook (worker systemd unit).
- **Tests**: `tests/test_protected_routes_auth.py` (Phase A), `tests/test_repositories_live.py` (Phase B), `tests/test_worker_live.py` (Phase D), `tests/test_foundation_structure.py` (add 0005).
- **Frontend (Phase A)**: `api/client.ts` (Bearer token + 401 logout, drop userId in payloads/query), `pipeline/stepN/api.ts` + `types.ts`, `App.tsx`, `AuthGate.tsx`, `TerminalPanel.tsx`, `useTerminalReplay.ts`, `AutoRunPanel.tsx`, `AiAutoRunWindow.tsx`.