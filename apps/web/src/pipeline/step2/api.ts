import type { Step2RunRequest } from "./types";

function toApiConfig(request: Step2RunRequest) {
  return {
    page_batch_size: request.config.pageBatchSize,
    internal_page_concurrency: request.config.internalPageConcurrency,
    extraction_prompt_id: request.config.extractionPromptId,
    metadata_defaults: request.config.metadataDefaults,
    metadata_strategies: request.config.metadataStrategies,
    legacy_subcategory_policy: request.config.legacySubcategoryPolicy,
    template_name: request.config.templateName,
    template_overrides: request.config.templateOverrides,
    output_format: request.config.outputFormat,
    resume_from_cycle: request.config.resumeFromCycle,
    model: {
      provider: request.config.model.provider,
      primary_model_id: request.config.model.primaryModelId,
      fallback_model_ids: request.config.model.fallbackModelIds
    }
  };
}

export async function runCombinedStep2(request: Step2RunRequest, correlationId: string) {
  const response = await fetch(`/projects/${request.projectId}/steps/step2/run`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-correlation-id": correlationId
    },
    body: JSON.stringify({
      user_id: request.userId,
      run_id: request.runId,
      step1_artifact_ids: request.step1ArtifactIds,
      pages: request.pages.map((page) => ({
        page_number: page.pageNumber,
        text: page.text,
        source_artifact_id: page.sourceArtifactId
      })),
      config: toApiConfig(request),
      idempotency_key: request.idempotencyKey
    })
  });
  if (!response.ok) {
    throw new Error(`Combined Step 2 run request failed with ${response.status}`);
  }
  return response.json();
}
