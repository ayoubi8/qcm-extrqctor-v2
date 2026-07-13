export type AiAutoRunAction = "retry" | "cancel" | "continue";

export interface AiAutoRunDraft {
  aiRunId: string;
  primaryModelId: string;
  fallbackModelIds: string[];
  templateName: string;
  correctionMode: "page_detection" | "vision" | "auto_detection";
}

export interface AiAutoRunWindowState {
  open: boolean;
  minimized: boolean;
}
