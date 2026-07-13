import type { Step1RunRequest } from "./types";

function toApiConfig(request: Step1RunRequest) {
  return {
    extraction_mode: request.config.extractionMode,
    override_reason: request.config.overrideReason,
    page_range_start: request.config.pageRangeStart,
    page_range_end: request.config.pageRangeEnd,
    text_fixer_enabled: request.config.textFixerEnabled,
    text_fixer_model: request.config.textFixerModel
  };
}

export async function runStep1(request: Step1RunRequest, correlationId: string) {
  const response = await fetch(`/projects/${request.projectId}/step1/run`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-correlation-id": correlationId
    },
    body: JSON.stringify({
      user_id: request.userId,
      run_id: request.runId,
      source_file_id: request.sourceFileId,
      source_filename: request.sourceFilename,
      idempotency_key: request.idempotencyKey,
      config: toApiConfig(request)
    })
  });
  if (!response.ok) {
    throw new Error(`Step 1 run request failed with ${response.status}`);
  }
  return response.json();
}
