export interface ArtifactVersionItem {
  artifactVersionId: string;
  artifactId: string;
  artifactType: string;
  filename: string;
  contentType: string;
  versionNumber: number;
  createdAt: string;
  sizeBytes: number;
  runId?: string | null;
}

export interface ResultGroup {
  runId: string;
  title: string;
  artifacts: ArtifactVersionItem[];
}
