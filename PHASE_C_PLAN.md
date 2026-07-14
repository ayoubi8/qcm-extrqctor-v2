# Phase C Implementation Plan — Storage: Real Signed URLs & Working Uploads

## The Problem (What's Broken Today)

When a user creates a project and picks a source PDF, here's what happens:

1. **Frontend** calls `POST /uploads/init` — the API validates the file size (50 MB cap) and returns a `storage_key` (the path where the file should be stored). **But the file is never actually uploaded anywhere** — the frontend just calls `initializeUpload` and moves on.

2. **`RuntimeArtifactService.create_signed_url`** returns `signed_url=""` (empty string) — so when the user clicks "Download" on an artifact, the URL is blank and nothing happens.

3. **No artifact persistence** — step handlers write to `InMemoryStep1ArtifactSink` which dies when the function returns. No `artifacts` or `artifact_versions` rows are ever created in Supabase.

4. **The snapshot's `artifacts` array is always `[]`** — the frontend shows fake demo artifacts instead of real ones.

**Bottom line:** uploads are a dead end, downloads don't work, and no artifacts are persisted.

---

## The Supabase Storage Setup (Already Done)

Your Supabase project already has:
- A **private bucket** called `qcm-artifacts-private` (created 2026-07-14, public=false)
- The **Storage REST API** is accessible at `https://rrirgkkawlnyigfaevja.supabase.co/storage/v1/`
- Authentication via the `apikey` header + `Authorization: Bearer` header (service-role key for server-side, anon key for client-side)

The Supabase Storage REST API supports:
- **Upload**: `POST /storage/v1/object/{bucket}/{path}` — file in body, `Content-Type` header set, apikey+Authorization headers
- **Signed URL**: `POST /storage/v1/object/sign/{bucket}/{path}` — body `{"expiresIn": 900}` → returns `{"signedURL": "https://..."}`
- **Download via signed URL**: `GET {signedURL}` — public, no auth needed (time-limited)
- **Delete**: `DELETE /storage/v1/object/{bucket}/{path}`

---

## What I Will Build (Step by Step)

### C1. `SupabaseStorageRestAdapter` — direct-to-Storage via httpx

**What:** A new storage adapter that talks to the Supabase Storage REST API using `httpx` (no `supabase-py` SDK needed — keeps dependencies minimal, same pattern as the PostgREST client).

**How:** New file `packages/infrastructure/src/qcm_infrastructure/storage/rest_adapter.py`:
- `SupabaseStorageRestAdapter(base_url, api_key, service_role, bucket_name)`
- `put(storage_key, content, content_type)` → `POST /storage/v1/object/{bucket}/{storage_key}` with the bytes in the body
- `create_signed_url(storage_key, expires_in_seconds)` → `POST /storage/v1/object/sign/{bucket}/{storage_key}` with `{"expiresIn": N}` → extracts `signedURL` from the response
- `delete_many(storage_keys)` → `DELETE /storage/v1/object/{bucket}/{storage_key}` for each key
- It implements the existing `ObjectStorage` Protocol from `artifact_service.py` so it's a drop-in replacement for the in-memory adapter

**Why:** The existing `SupabaseStorageAdapter` in `supabase_adapter.py` requires a `supabase-py` SDK client object (which isn't installed and is a heavy dep). Using `httpx` directly to the REST API mirrors how we already talk to PostgREST — one dependency, one pattern. The adapter is service-role authenticated (the API process holds the service-role key).

### C2. `SupabaseArtifactRepository` — persist artifact + version rows

**What:** A new repository that writes `artifacts` (parent) and `artifact_versions` (child) rows to Supabase Postgres, matching the migration 0002 schema.

**How:** Added to `packages/infrastructure/src/qcm_infrastructure/db/repositories.py`:
- `SupabaseArtifactRepository(client: PostgrestClient)`
- `create_artifact(artifact_id, user_id, project_id, artifact_type, run_id)` → inserts into `artifacts` table, returns the row
- `create_version(request: ArtifactWriteRequest, storage_key)` → inserts into `artifact_versions` table (with `checksum`, `size_bytes`, `schema_version`, `retention_policy`, `source_artifact_ids`), updates `artifacts.latest_version_id`
- `get_version_for_signed_url(artifact_version_id)` → reads `artifact_versions` + `artifacts` for ownership check
- `list_versions_for_project(user_id, project_id)` → for the snapshot endpoint
- `create_source_file(user_id, project_id, filename, storage_key, content_type, size_bytes, checksum)` → inserts a `source_files` row (needed for Step 1 to reference the uploaded PDF)

**Why:** Without this, produced artifacts vanish — the step handlers write to in-memory sinks that die with the function. The `artifacts` table is the parent that groups versions; `artifact_versions` is the append-only child that records each specific file. The `source_files` table records uploaded PDFs so Step 1 can reference them.

### C3. Wire `RuntimeArtifactService` to use real storage + artifact repo

**What:** Replace the stub `RuntimeArtifactService` in `runtime.py` with one that uses the real storage adapter and artifact repository.

**How:** 
- `RuntimeArtifactService.__init__` accepts a `storage` adapter (SupabaseStorageRestAdapter) and `artifact_repo` (SupabaseArtifactRepository)
- `initialize_upload` stays the same (validates 50 MB, returns the storage_key path)
- `create_signed_url` calls the real `storage.create_signed_url(storage_key, expires)` and returns a real URL
- `upload_source_file(user_id, project_id, filename, content, content_type)` — **new method** that:
  1. Validates file size ≤ 50 MB
  2. Builds the storage key (`users/{uid}/projects/{pid}/artifacts/source_pdf/{aid}/v0001/{filename}`)
  3. Calls `storage.put(key, content, content_type)` to upload to Supabase Storage
  4. Computes SHA-256 checksum
  5. Creates a `source_files` row
  6. Creates an `artifacts` + `artifact_versions` row
  7. Returns `{ source_file_id, artifact_id, artifact_version_id, storage_key }`

**Why:** This is the core plumbing — the API now can accept a file from the user, store it in Supabase Storage, and record metadata in Postgres. Without this, uploads don't persist and Step 1 has nothing to work with.

### C4. New API endpoint: `POST /uploads/{project_id}/source-file`

**What:** A server-side upload proxy endpoint that receives the file from the frontend and uploads it to Supabase Storage.

**How:** New route in `apps/api/src/qcm_api/routes/artifacts.py`:
- `POST /uploads/{project_id}/source-file` — accepts `multipart/form-data` (file + optional filename override)
- Protected by the `current_user` dependency (user_id from JWT)
- Calls `RuntimeArtifactService.upload_source_file(user_id, project_id, filename, content_bytes, content_type)`
- Returns `{ source_file_id, artifact_id, artifact_version_id, storage_key, allowed: true }`

**Why — server-side proxy vs direct browser upload:**
I chose a server-side proxy (the file goes through the API) instead of a direct browser-to-Supabase upload because:
1. **No CORS configuration needed** on the Supabase Storage bucket — the VPS API talks to Supabase server-to-server
2. **Service-role authentication** — the upload uses the service-role key (server-side), not the anon key (browser-side), so the bucket can stay fully private
3. **Metadata creation is atomic with the upload** — if the file uploads but the DB insert fails, we can clean up; if the DB insert fails first, we don't upload a orphan
4. **Simpler frontend** — the frontend just sends a `FormData` POST to the same API base URL it already uses; no need to know the Supabase URL or handle storage-specific errors
5. The 50 MB file size limit is small enough that the bandwidth doubling (browser → VPS → Supabase) is acceptable for this use case

### C5. Frontend: actually send the file after project creation

**What:** Update the frontend `PipelinePage.tsx` to upload the PDF file when a project is created.

**How:** In `PipelinePage.tsx`, the `createProjectMutation` currently calls `initializeUpload` (validates size) and moves on. I'll change it to:
1. Call `POST /uploads/init` (validates size, returns storage_key) — already done
2. **NEW:** Call `POST /uploads/{project_id}/source-file` with the actual file as `FormData`
3. Store the returned `source_file_id` + `artifact_version_id` for later use

New function in `client.ts`:
- `uploadSourceFile(projectId, file, correlationId)` → sends `FormData` to `/uploads/{projectId}/source-file`

**Why:** Today the file is never sent to any server — it's just a `<File>` object in the browser. This step actually pushes the bytes to the API, which stores them in Supabase Storage.

### C6. Update the snapshot to include real artifacts

**What:** The `snapshot` endpoint's `artifacts` array is currently always `[]`. Populate it from the `artifact_versions` table.

**How:** In `RuntimeProjectService.snapshot()`, call `artifact_repo.list_versions_for_project(user_id, project_id)` and map rows to the frontend's `ArtifactVersionSummary` format.

**Why:** The frontend's "Result hub" panel shows demo artifacts (`demo-step1-v1`, etc.) instead of real ones. With this, the user sees their actual uploaded PDFs and produced artifacts.

### C7. Make the "Download" button work

**What:** When the user clicks "Download" on an artifact, the frontend calls `GET /artifact-versions/{id}/signed-url` which should return a real Supabase Storage signed URL.

**How:** The backend route already exists (`artifacts.py` `signed_url` endpoint) and now uses the real `RuntimeArtifactService.create_signed_url` (C3). The frontend's `signedUrl` mutation in `PipelinePage.tsx` already fetches and displays the URL. I just need to make sure the frontend opens/redirects to the signed URL so the browser downloads the file.

**Why:** Today `signed_url` returns `""` so the download button does nothing. After C3, it returns a real time-limited URL from Supabase Storage, and the browser can download the artifact.

---

## Data Flow (After Phase C)

```
User picks PDF → clicks "Create project"
  ↓
Frontend: POST /projects           → API creates project row in Supabase
  ↓
Frontend: POST /uploads/init       → API validates 50 MB cap, returns storage_key
  ↓
Frontend: POST /uploads/{pid}/source-file (FormData with file bytes)
  ↓
API: validates size → uploads to Supabase Storage → creates source_files row
  ↓                                                              → creates artifacts row
  ↓                                                              → creates artifact_versions row
  ↓
API returns { source_file_id, artifact_id, artifact_version_id }
  ↓
Frontend stores IDs, refreshes snapshot
  ↓
Snapshot now shows the source PDF in the artifacts list
  ↓
User clicks "Download" on an artifact
  ↓
Frontend: GET /artifact-versions/{id}/signed-url
  ↓
API: looks up version → checks ownership → calls Storage signed URL API → returns real URL
  ↓
Frontend opens the signed URL → browser downloads the file
```

---

## Files I Will Create/Modify

| File | Action | Purpose |
|---|---|---|
| `packages/infrastructure/.../storage/rest_adapter.py` | **New** | httpx-based Supabase Storage REST adapter |
| `packages/infrastructure/.../db/repositories.py` | **Modify** | Add `SupabaseArtifactRepository` + `SupabaseSourceFileRepository` |
| `apps/api/.../runtime.py` | **Modify** | Wire real storage + artifact repo into `RuntimeArtifactService` |
| `apps/api/.../routes/artifacts.py` | **Modify** | Add `POST /uploads/{project_id}/source-file` endpoint |
| `apps/web/src/api/client.ts` | **Modify** | Add `uploadSourceFile()` function |
| `apps/web/src/pipeline/PipelinePage.tsx` | **Modify** | Send file after project creation, use real artifacts |
| `apps/web/src/projects/ProjectLauncher.tsx` | **Modify** | Show upload progress |
| `tests/test_storage_live.py` | **New** | Live test: upload → create version → signed URL → download |

---

## What Will NOT Be Fixed in Phase C

- **Step handler artifact writes** — the handlers still write to `InMemory*ArtifactSink`. Making them write to Supabase Storage is Phase E (when real PDF extraction produces real output). Phase C only makes **source file uploads** and **downloads** work.
- **CORS on the Storage bucket** — not needed because uploads go through the API (server-side proxy), not direct from the browser.
- **Cleanup/retention** — the `cleanup_storage_versions` function exists but isn't wired to a worker handler yet. Deferred to a later phase.

---

## Verification Plan

1. **Live test** (`tests/test_storage_live.py`): upload a test file to Supabase Storage → create an `artifact_versions` row → get a signed URL → fetch the file via the signed URL → verify content matches → clean up
2. **E2E on the VPS**: register → create project → upload a real PDF → snapshot shows the PDF artifact → download it via signed URL → verify file content
3. **Local tests**: all existing tests stay green (in-memory fallback when Supabase env not set)
4. **Frontend**: `tsc && vite build` passes with the new upload function

---

## Deployment Steps (After I Implement + Push)

```bash
# On the VPS
cd /opt/qcm-extractor-api/current
sudo git -c safe.directory=/opt/qcm-extractor-api/current pull origin main
sudo systemctl restart qcm-extractor-api
# Worker doesn't need restart (no worker changes in Phase C)
curl http://127.0.0.1:8000/health
```

No Supabase Storage bucket creation needed (already exists as `qcm-artifacts-private`).
No Supabase Storage policies needed (server-side uploads use the service-role key which bypasses RLS).
No new Python dependencies (uses `httpx` which is already installed).
No frontend build needed on the VPS (frontend is deployed separately, e.g. Vercel).