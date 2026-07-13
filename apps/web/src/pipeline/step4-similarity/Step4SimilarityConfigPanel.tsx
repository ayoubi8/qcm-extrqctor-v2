import { FileSpreadsheet, RotateCcw } from "lucide-react";
import type { Step4SimilarityConfig, Step4SimilarityMode } from "./types";

const modes: Step4SimilarityMode[] = ["text_only", "full", "weighted"];

interface Step4SimilarityConfigPanelProps {
  value: Step4SimilarityConfig;
  onChange: (value: Step4SimilarityConfig) => void;
  onRun: () => void;
}

export function Step4SimilarityConfigPanel({ value, onChange, onRun }: Step4SimilarityConfigPanelProps) {
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
      <div className="grid gap-3 sm:grid-cols-4">
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Reference DB"
          value={value.referenceDbId}
          onChange={(event) => onChange({ ...value, referenceDbId: event.target.value })}
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          type="number"
          min={0}
          max={1}
          step={0.01}
          value={value.threshold}
          onChange={(event) => onChange({ ...value, threshold: Number(event.target.value) })}
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          type="number"
          min={0}
          step={0.1}
          value={value.textWeight}
          onChange={(event) => onChange({ ...value, textWeight: Number(event.target.value) })}
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          type="number"
          min={0}
          step={0.1}
          value={value.correctionWeight}
          onChange={(event) => onChange({ ...value, correctionWeight: Number(event.target.value) })}
        />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={value.exportExisting}
            onChange={(event) => onChange({ ...value, exportExisting: event.target.checked })}
          />
          Export existing
        </label>
        <input
          className="w-48 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Export QCM IDs"
          value={value.exportQcmIds.join(",")}
          onChange={(event) =>
            onChange({
              ...value,
              exportQcmIds: event.target.value
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean)
            })
          }
        />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-cyan-300 bg-cyan-300 px-3 py-2 text-sm font-medium text-slate-950"
          onClick={onRun}
        >
          <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
          Run Match
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-slate-700 px-3 py-2 text-sm text-slate-200"
          onClick={() =>
            onChange({
              referenceDbId: "",
              mode: "text_only",
              threshold: 0.75,
              textWeight: 0.7,
              correctionWeight: 0.3,
              colorGreen: 0.9,
              colorYellow: 0.75,
              exportExisting: false,
              exportQcmIds: []
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
