import { History, RotateCcw } from "lucide-react";
import { Button, Card, StatusBadge } from "../components/ui";
import type { ProjectHistoryItem } from "./types";

interface HistoryRestorePanelProps {
  items: ProjectHistoryItem[];
  selectedProjectId?: string;
  onRestore: (projectId: string) => void;
}

export function HistoryRestorePanel({ items, selectedProjectId, onRestore }: HistoryRestorePanelProps) {
  return (
    <Card title="History restore" actions={<History className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
      <div className="grid gap-3">
        {items.map((item) => (
          <div
            key={item.projectId}
            className={`grid gap-3 rounded-md border p-3 sm:grid-cols-[1fr_auto] ${
              selectedProjectId === item.projectId ? "border-cyan-400/60 bg-cyan-400/10" : "border-slate-800 bg-slate-950"
            }`}
          >
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-slate-100">{item.name}</span>
                <StatusBadge tone={item.status === "failed" ? "danger" : "info"}>{item.status}</StatusBadge>
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {item.artifactCount} artifacts | {item.updatedAt}
              </div>
            </div>
            <Button variant="secondary" icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />} onClick={() => onRestore(item.projectId)}>
              Restore
            </Button>
          </div>
        ))}
      </div>
    </Card>
  );
}
