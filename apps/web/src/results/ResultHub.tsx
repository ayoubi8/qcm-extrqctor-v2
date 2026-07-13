import { Card, StatusBadge } from "../components/ui";
import type { ArtifactVersionItem } from "./types";

interface ResultHubProps {
  artifacts: ArtifactVersionItem[];
  selectedArtifactVersionId: string | null;
  onSelectArtifact: (artifactVersionId: string) => void;
}

export function ResultHub({ artifacts, selectedArtifactVersionId, onSelectArtifact }: ResultHubProps) {
  return (
    <Card title="Results">
      <div className="grid gap-2">
        {artifacts.length === 0 ? (
          <p className="text-sm text-slate-500">No artifacts are available for the selected run yet.</p>
        ) : (
          artifacts.map((artifact) => (
            <button
              key={artifact.artifactVersionId}
              type="button"
              className={`grid gap-2 rounded-md border p-3 text-left transition-colors ${
                selectedArtifactVersionId === artifact.artifactVersionId
                  ? "border-cyan-400/60 bg-cyan-400/10"
                  : "border-slate-800 bg-slate-950 hover:border-slate-700"
              }`}
              onClick={() => onSelectArtifact(artifact.artifactVersionId)}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-100">{artifact.filename}</span>
                <StatusBadge tone="neutral">v{artifact.versionNumber}</StatusBadge>
              </div>
              <span className="text-xs text-slate-500">{artifact.artifactType}</span>
            </button>
          ))
        )}
      </div>
    </Card>
  );
}
