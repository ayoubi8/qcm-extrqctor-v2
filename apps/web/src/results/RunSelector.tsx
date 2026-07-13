import type { RunSummary } from "../api/client";

interface RunSelectorProps {
  runs: RunSummary[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
}

export function RunSelector({ runs, selectedRunId, onSelect }: RunSelectorProps) {
  return (
    <label className="grid gap-2 text-sm text-slate-300">
      <span>Run</span>
      <select
        className="min-h-10 rounded-md border border-slate-700 bg-slate-950 px-3 text-sm"
        value={selectedRunId ?? ""}
        onChange={(event) => onSelect(event.target.value)}
      >
        {runs.map((run) => (
          <option key={run.runId} value={run.runId}>
            {run.label} | {run.status}
          </option>
        ))}
      </select>
    </label>
  );
}
