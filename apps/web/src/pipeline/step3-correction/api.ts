import { requestJson } from "../../api/client";
import type { Step3CorrectionRunRequest } from "./types";

function toApiConfig(request: Step3CorrectionRunRequest) {
  return {
    mode: request.config.mode,
    selected_pages: request.config.selectedPages,
    candidate_threshold: request.config.candidateThreshold,
    include_neighbors: request.config.includeNeighbors,
    force_overwrite: request.config.forceOverwrite,
    vision_guide: request.config.visionGuide,
    vision_detections: request.config.visionDetections
  };
}

export async function runStep3Correction(request: Step3CorrectionRunRequest, correlationId: string) {
  return requestJson(`/projects/${request.projectId}/steps/step3-correction/run`, {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({
      run_id: request.runId,
      step2_artifact_ids: request.step2ArtifactIds,
      qcms: request.qcms,
      pages: request.pages.map((page) => ({
        page_number: page.pageNumber,
        text: page.text,
        source_artifact_id: page.sourceArtifactId
      })),
      config: toApiConfig(request),
      idempotency_key: request.idempotencyKey
    })
  });
}