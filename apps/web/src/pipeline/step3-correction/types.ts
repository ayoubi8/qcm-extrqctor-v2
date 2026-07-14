export type Step3CorrectionMode = "page_detection" | "vision" | "auto_detection";

export interface Step3CorrectionConfig {
  mode: Step3CorrectionMode;
  selectedPages: number[];
  candidateThreshold: number;
  includeNeighbors: boolean;
  forceOverwrite: boolean;
  visionGuide?: string;
  visionDetections: Record<string, string>;
}

export interface Step3CorrectionPage {
  pageNumber: number;
  text: string;
  sourceArtifactId?: string;
}

export interface Step3CorrectionRunRequest {
  projectId: string;
  runId: string;
  step2ArtifactIds: string[];
  qcms: Record<string, unknown>[];
  pages: Step3CorrectionPage[];
  config: Step3CorrectionConfig;
  idempotencyKey: string;
}
