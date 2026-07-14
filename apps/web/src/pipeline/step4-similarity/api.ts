import { listReferenceDbs as listReferenceDbsFromClient, requestJson } from "../../api/client";
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
  return requestJson(`/projects/${request.projectId}/steps/step4-similarity/run`, {
    method: "POST",
    headers: { "x-correlation-id": correlationId },
    body: JSON.stringify({
      run_id: request.runId,
      source_artifact_ids: request.sourceArtifactIds,
      source_qcms: request.sourceQcms,
      reference_qcms: request.referenceQcms,
      existing_matches: request.existingMatches,
      config: toApiConfig(request),
      idempotency_key: request.idempotencyKey
    })
  });
}

export function listReferenceDbs() {
  return listReferenceDbsFromClient();
}