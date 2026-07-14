export type Step2OutputFormat = "json" | "json+xlsx";

export interface Step2ModelConfig {
  provider: "openrouter";
  primaryModelId: string;
  fallbackModelIds: string[];
}

export interface Step2Config {
  pageBatchSize: number;
  internalPageConcurrency: number;
  extractionPromptId: string;
  metadataDefaults: Record<string, string>;
  metadataStrategies: Record<string, string>;
  legacySubcategoryPolicy: "preserve_internal" | "export" | "drop";
  templateName: string;
  templateOverrides: Record<string, unknown>;
  outputFormat: Step2OutputFormat;
  model: Step2ModelConfig;
  resumeFromCycle?: "step2_qcm_pages" | "step2_metadata" | "step2_format" | "step2_finalize";
}

export interface Step2SourcePage {
  pageNumber: number;
  text: string;
  sourceArtifactId?: string;
}

export interface Step2RunRequest {
  projectId: string;
  runId: string;
  step1ArtifactIds: string[];
  pages: Step2SourcePage[];
  config: Step2Config;
  idempotencyKey: string;
}
