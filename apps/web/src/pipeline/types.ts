export type PipelineStepId = "step1" | "step2" | "step3-correction" | "step4-similarity";

export type PipelineStepStatus = "locked" | "ready" | "queued" | "running" | "completed" | "warning" | "failed";

export interface PipelineStepState {
  id: PipelineStepId;
  order: number;
  title: string;
  taskKind: string;
  status: PipelineStepStatus;
  artifactTypes: string[];
  lastRunId?: string;
  warnings: string[];
}

export interface PipelineRunContext {
  userId: string;
  projectId: string;
  runId: string;
  sourceArtifactIds: string[];
}
