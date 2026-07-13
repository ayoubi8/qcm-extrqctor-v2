import type { TerminalPage } from "../terminal/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ProjectSummary {
  project_id: string;
  user_id: string;
  name: string;
  status: string;
  updated_at: string;
}

export interface ProjectCreateRequest {
  userId: string;
  name: string;
  idempotencyKey: string;
}

export interface UploadInitRequest {
  userId: string;
  projectId: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  idempotencyKey: string;
}

export interface UploadInitResponse {
  allowed: boolean;
  storage_key?: string | null;
  provider_limit_event: string;
  safe_message?: string | null;
}

export interface ArtifactVersionSummary {
  artifactVersionId: string;
  artifactId: string;
  artifactType: string;
  filename: string;
  contentType: string;
  versionNumber: number;
  createdAt: string;
  sizeBytes: number;
  runId?: string | null;
  checksum?: string | null;
}

export interface RunSummary {
  runId: string;
  projectId: string;
  label: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface TaskSummary {
  taskId: string;
  kind: string;
  status: string;
  runId: string;
  updatedAt: string;
  safeMessage?: string | null;
}

export interface ProjectSnapshot {
  project: ProjectSummary;
  runs: RunSummary[];
  tasks: TaskSummary[];
  artifacts: ArtifactVersionSummary[];
}

export interface TaskCreateRequest {
  userId: string;
  projectId: string;
  runId: string;
  kind: string;
  idempotencyKey: string;
  payload: Record<string, unknown>;
  priority?: number;
}

export interface ManualAutoRunStepConfig {
  step_key: string;
  task_kind: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface ManualAutoRunSnapshot {
  schema_version: "manual-autorun.v1";
  selected_steps: ManualAutoRunStepConfig[];
  saved_defaults: Record<string, unknown>;
  project_overrides: Record<string, unknown>;
  resource_limits: Record<string, unknown>;
}

export interface ManualAutoRunStartRequest {
  userId: string;
  projectId: string;
  runId: string;
  autoRunId: string;
  snapshot: ManualAutoRunSnapshot;
  idempotencyKey: string;
}

export interface AiAutoRunPageInput {
  page_number: number;
  text: string;
  source_artifact_id?: string | null;
}

export interface AiAutoRunStartRequest {
  userId: string;
  projectId: string;
  runId: string;
  aiRunId: string;
  pages: AiAutoRunPageInput[];
  modelSelection: {
    provider: "openrouter";
    primary_model_id: string;
    fallback_model_ids: string[];
  };
  userConstraints: Record<string, unknown>;
  idempotencyKey: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

export function createProject(request: ProjectCreateRequest, correlationId: string) {
  return requestJson<ProjectSummary>("/projects", {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({
      user_id: request.userId,
      name: request.name,
      idempotency_key: request.idempotencyKey
    })
  });
}

export function initializeUpload(request: UploadInitRequest) {
  return requestJson<UploadInitResponse>("/uploads/init", {
    method: "POST",
    body: JSON.stringify({
      user_id: request.userId,
      project_id: request.projectId,
      filename: request.filename,
      content_type: request.contentType,
      size_bytes: request.sizeBytes,
      idempotency_key: request.idempotencyKey
    })
  });
}

export function createTask(request: TaskCreateRequest, correlationId: string) {
  return requestJson<TaskSummary>("/tasks", {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({
      user_id: request.userId,
      project_id: request.projectId,
      run_id: request.runId,
      kind: request.kind,
      idempotency_key: request.idempotencyKey,
      payload: request.payload,
      priority: request.priority ?? 0
    })
  });
}

export function cancelTask(taskId: string, actorUserId: string, correlationId: string) {
  return requestJson<TaskSummary>(`/tasks/${taskId}/cancel`, {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({ actor_user_id: actorUserId })
  });
}

export function fetchTerminalPage(projectId: string, userId: string, afterSequence?: number | null) {
  const params = new URLSearchParams({ user_id: userId });
  if (afterSequence) {
    params.set("after_sequence", String(afterSequence));
  }
  return requestJson<TerminalPage>(`/projects/${projectId}/terminal?${params.toString()}`);
}

export function fetchSignedUrl(artifactVersionId: string, correlationId: string, expiresInSeconds = 900) {
  return requestJson<{ signed_url: string; expires_in_seconds: number }>(
    `/artifact-versions/${artifactVersionId}/signed-url?expires_in_seconds=${expiresInSeconds}`,
    { headers: { "x-correlation-id": correlationId } }
  );
}

export function fetchProjectSnapshot(projectId: string, userId: string) {
  const params = new URLSearchParams({ user_id: userId });
  return requestJson<ProjectSnapshot>(`/projects/${projectId}/snapshot?${params.toString()}`);
}

export function validateManualAutoRun(projectId: string, snapshot: ManualAutoRunSnapshot) {
  return requestJson<{ valid: boolean; errors: string[]; warnings: string[] }>(`/projects/${projectId}/manual-autoruns/validate`, {
    method: "POST",
    body: JSON.stringify({ snapshot })
  });
}

export function startManualAutoRun(request: ManualAutoRunStartRequest, correlationId: string) {
  return requestJson<{ auto_run_id: string; status: string; child_task_ids: string[] }>(
    `/projects/${request.projectId}/manual-autoruns`,
    {
      method: "POST",
      headers: { "x-correlation-id": correlationId },
      body: JSON.stringify({
        user_id: request.userId,
        run_id: request.runId,
        auto_run_id: request.autoRunId,
        snapshot: request.snapshot,
        idempotency_key: request.idempotencyKey
      })
    }
  );
}

export function controlManualAutoRun(
  projectId: string,
  autoRunId: string,
  action: "pause" | "resume" | "retry" | "cancel",
  userId: string,
  correlationId: string
) {
  return requestJson<{ auto_run_id: string; status: string }>(`/projects/${projectId}/manual-autoruns/${autoRunId}/${action}`, {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({ user_id: userId })
  });
}

export function startAiAutoRun(request: AiAutoRunStartRequest, correlationId: string) {
  return requestJson<{ ai_run_id: string; status: string; artifact_ids: string[] }>(
    `/projects/${request.projectId}/ai-autoruns`,
    {
      method: "POST",
      headers: { "x-correlation-id": correlationId },
      body: JSON.stringify({
        user_id: request.userId,
        run_id: request.runId,
        ai_run_id: request.aiRunId,
        pages: request.pages,
        model_selection: request.modelSelection,
        user_constraints: request.userConstraints,
        idempotency_key: request.idempotencyKey
      })
    }
  );
}

export function actionAiAutoRun(
  projectId: string,
  aiRunId: string,
  action: "retry" | "cancel" | "continue",
  userId: string,
  correlationId: string
) {
  return requestJson<{ ai_run_id: string; status: string }>(`/projects/${projectId}/ai-autoruns/${aiRunId}/${action}`, {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({ user_id: userId })
  });
}
