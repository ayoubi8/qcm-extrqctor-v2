export interface ProjectDraft {
  name: string;
  file?: File | null;
}

export interface ProjectHistoryItem {
  projectId: string;
  name: string;
  status: "active" | "archived" | "failed" | "draft";
  updatedAt: string;
  latestRunId?: string;
  artifactCount: number;
}
