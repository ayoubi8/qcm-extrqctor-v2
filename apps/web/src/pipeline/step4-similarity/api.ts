import { API_BASE_URL } from "../../config/apiBaseUrl";
import type { Step4SimilarityRunRequest } from "./types";

function toApiConfig(request: Step4SimilarityRunRequest) {
  return {
    reference_db_id: request.config.referenceDbId,
    mode: request.config.mode,
    threshold: request.config.threshold,
    text_weight: request.config.textWeight,
    correction_weight: request.config.correctionWeight,
    color_green: request.config.colorGreen,
    color_yellow: request.config.colorYellow,
    export_existing: request.config.exportExisting,
    export_min_similarity: request.config.exportMinSimilarity,
    export_max_similarity: request.config.exportMaxSimilarity,
    export_qcm_ids: request.config.exportQcmIds
  };
}

export async function runStep4Similarity(request: Step4SimilarityRunRequest, correlationId: string) {
  const response = await fetch(`${API_BASE_URL}/projects/${request.projectId}/steps/step4-similarity/run`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-correlation-id": correlationId
    },
    body: JSON.stringify({
      user_id: request.userId,
      run_id: request.runId,
      source_artifact_ids: request.sourceArtifactIds,
      source_qcms: request.sourceQcms,
      reference_qcms: request.referenceQcms,
      existing_matches: request.existingMatches,
      config: toApiConfig(request),
      idempotency_key: request.idempotencyKey
    })
  });
  if (!response.ok) {
    throw new Error(`Step 4 similarity run request failed with ${response.status}`);
  }
  return response.json();
}

export async function listReferenceDbs(userId: string) {
  const response = await fetch(`${API_BASE_URL}/reference-dbs?user_id=${encodeURIComponent(userId)}`);
  if (!response.ok) {
    throw new Error(`Reference DB list request failed with ${response.status}`);
  }
  return response.json();
}
