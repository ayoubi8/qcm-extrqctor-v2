export type Step1ExtractionMode = "automatic" | "direct" | "ocr" | "mixed";

export interface Step1Config {
  extractionMode: Step1ExtractionMode;
  overrideReason?: string;
  pageRangeStart?: number;
  pageRangeEnd?: number;
  textFixerEnabled: boolean;
  textFixerModel?: string;
}

export interface Step1RunRequest {
  projectId: string;
  runId: string;
  sourceFileId: string;
  sourceFilename: string;
  config: Step1Config;
  idempotencyKey: string;
}

export interface Step1DetectionSummary {
  requestedMode: Step1ExtractionMode;
  resolvedMode: Step1ExtractionMode;
  manualOverride: boolean;
  warnings: string[];
}
