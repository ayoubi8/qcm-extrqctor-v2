export type ManualAutoRunControlAction = "pause" | "resume" | "retry" | "cancel";

export interface ManualAutoRunStepDraft {
  stepKey: string;
  taskKind: string;
  enabled: boolean;
  config: Record<string, unknown>;
}

export interface ManualAutoRunDraft {
  autoRunId: string;
  selectedSteps: ManualAutoRunStepDraft[];
  saveAsDefaults: boolean;
  projectOverrides: Record<string, unknown>;
  resourceLimits: Record<string, unknown>;
}

export interface ManualAutoRunNotice {
  tone: "success" | "warning" | "danger";
  message: string;
}
