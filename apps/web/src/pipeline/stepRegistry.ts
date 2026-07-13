import type { PipelineStepState } from "./types";

export const pipelineSteps: PipelineStepState[] = [
  {
    id: "step1",
    order: 1,
    title: "Text Extraction",
    taskKind: "step1_extract",
    status: "ready",
    artifactTypes: ["step1_text", "page_text"],
    warnings: []
  },
  {
    id: "step2",
    order: 2,
    title: "QCM Extraction",
    taskKind: "step2_orchestrate",
    status: "locked",
    artifactTypes: ["step2_final_json", "step2_final_xlsx"],
    warnings: []
  },
  {
    id: "step3-correction",
    order: 3,
    title: "Correction",
    taskKind: "step3_correction",
    status: "locked",
    artifactTypes: ["step3_correction_json", "step3_correction_xlsx"],
    warnings: []
  },
  {
    id: "step4-similarity",
    order: 4,
    title: "Similarity Match",
    taskKind: "step4_similarity_match",
    status: "locked",
    artifactTypes: ["step4_similarity_json", "step4_similarity_xlsx"],
    warnings: []
  }
];
