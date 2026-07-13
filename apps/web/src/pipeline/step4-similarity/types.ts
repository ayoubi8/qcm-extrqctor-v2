export type Step4SimilarityMode = "text_only" | "full" | "weighted";

export interface Step4SimilarityConfig {
  referenceDbId: string;
  mode: Step4SimilarityMode;
  threshold: number;
  textWeight: number;
  correctionWeight: number;
  colorGreen: number;
  colorYellow: number;
  exportExisting: boolean;
  exportMinSimilarity?: number;
  exportMaxSimilarity?: number;
  exportQcmIds: string[];
}

export interface Step4SimilarityRunRequest {
  userId: string;
  projectId: string;
  runId: string;
  sourceArtifactIds: string[];
  sourceQcms: Record<string, unknown>[];
  referenceQcms: Record<string, unknown>[];
  existingMatches: Record<string, unknown>[];
  config: Step4SimilarityConfig;
  idempotencyKey: string;
}

export interface ReferenceDbSummary {
  referenceDbId: string;
  userId: string;
  name: string;
  qcmCount: number;
  createdAt?: string;
}
