import { ScanSearch, RotateCcw } from "lucide-react";
import type { Step3CorrectionConfig, Step3CorrectionMode } from "./types";

const modes: Step3CorrectionMode[] = ["page_detection", "vision", "auto_detection"];

interface Step3CorrectionConfigPanelProps {
  value: Step3CorrectionConfig;
  onChange: (value: Step3CorrectionConfig) => void;
  onRun: () => void;
}

export function Step3CorrectionConfigPanel({ value, onChange, onRun }: Step3CorrectionConfigPanelProps) {
  return (
    <section className="grid gap-4 border-b border-slate-800 py-5">
      <div className="flex flex-wrap items-center gap-2">
        {modes.map((mode) => (
          <button
            key={mode}
            type="button"
            className={`rounded border px-3 py-2 text-sm ${
              value.mode === mode
                ? "border-cyan-300 bg-cyan-300 text-slate-950"
                : "border-slate-700 bg-slate-900 text-slate-200"
            }`}
            onClick={() => onChange({ ...value, mode })}
          >
            {mode}
          </button>
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Pages"
          value={value.selectedPages.join(",")}
          onChange={(event) =>
            onChange({
              ...value,
              selectedPages: event.target.value
                .split(",")
                .map((item) => Number(item.trim()))
                .filter((item) => Number.isFinite(item) && item > 0)
            })
          }
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          type="number"
          min={1}
          value={value.candidateThreshold}
          onChange={(event) => onChange({ ...value, candidateThreshold: Number(event.target.value) })}
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={value.includeNeighbors}
            onChange={(event) => onChange({ ...value, includeNeighbors: event.target.checked })}
          />
          Include neighbors
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-cyan-300 bg-cyan-300 px-3 py-2 text-sm font-medium text-slate-950"
          onClick={onRun}
        >
          <ScanSearch className="h-4 w-4" aria-hidden="true" />
          Run Correction
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-slate-700 px-3 py-2 text-sm text-slate-200"
          onClick={() =>
            onChange({
              mode: "page_detection",
              selectedPages: [],
              candidateThreshold: 15,
              includeNeighbors: true,
              forceOverwrite: false,
              visionDetections: {}
            })
          }
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Reset
        </button>
      </div>
    </section>
  );
}
