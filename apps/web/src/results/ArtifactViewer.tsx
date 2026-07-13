import { Download, FileJson, Sheet } from "lucide-react";
import { Button, Card, StatusBadge } from "../components/ui";
import type { ArtifactVersionItem } from "./types";

interface ArtifactViewerProps {
  artifact?: ArtifactVersionItem | null;
  onDownload: (artifactVersionId: string) => void;
}

export function ArtifactViewer({ artifact, onDownload }: ArtifactViewerProps) {
  if (!artifact) {
    return (
      <Card title="Artifact preview">
        <p className="text-sm text-slate-500">Select an artifact version to preview metadata and download access.</p>
      </Card>
    );
  }

  const isJson = artifact.contentType.includes("json");
  const Icon = isJson ? FileJson : Sheet;

  return (
    <Card
      title="Artifact preview"
      actions={<StatusBadge tone={isJson ? "info" : "success"}>{artifact.contentType}</StatusBadge>}
    >
      <div className="grid gap-4">
        <div className="flex items-start gap-3">
          <Icon className="mt-1 h-5 w-5 text-cyan-300" aria-hidden="true" />
          <div>
            <div className="text-sm font-medium text-slate-100">{artifact.filename}</div>
            <div className="mt-1 text-xs text-slate-500">
              v{artifact.versionNumber} | {artifact.sizeBytes} bytes | {artifact.createdAt}
            </div>
          </div>
        </div>
        <div className="rounded-md border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-400">
          artifactVersionId={artifact.artifactVersionId}
        </div>
        <Button variant="primary" icon={<Download className="h-4 w-4" aria-hidden="true" />} onClick={() => onDownload(artifact.artifactVersionId)}>
          Download
        </Button>
      </div>
    </Card>
  );
}
