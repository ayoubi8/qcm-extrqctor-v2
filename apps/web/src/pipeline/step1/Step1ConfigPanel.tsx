import { FileSearch, RotateCcw } from "lucide-react";
import type { Step1Config, Step1ExtractionMode } from "./types";

const modes: Step1ExtractionMode[] = ["automatic", "direct", "ocr", "mixed"];

interface Step1ConfigPanelProps {
  value: Step1Config;
  onChange: (value: Step1Config) => void;
  onRun: () => void;
}

export function Step1ConfigPanel({ value, onChange, onRun }: Step1ConfigPanelProps) {
  return (
    <section className="grid gap-4 border-b border-slate-800 py-5">
      <div className="flex flex-wrap items-center gap-2">
        {modes.map((mode) => (
          <button
            key={mode}
            type="button"
            className={`rounded border px-3 py-2 text-sm ${
              value.extractionMode === mode
                ? "border-cyan-300 bg-cyan-300 text-slate-950"
                : "border-slate-700 bg-slate-900 text-slate-200"
            }`}
            onClick={() => onChange({ ...value, extractionMode: mode })}
          >
            {mode}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={value.textFixerEnabled}
            onChange={(event) => onChange({ ...value, textFixerEnabled: event.target.checked })}
          />
          Text repair
        </label>
        <input
          className="min-w-60 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Override reason"
          value={value.overrideReason ?? ""}
          onChange={(event) => onChange({ ...value, overrideReason: event.target.value || undefined })}
        />
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-cyan-300 bg-cyan-300 px-3 py-2 text-sm font-medium text-slate-950"
          onClick={onRun}
        >
          <FileSearch className="h-4 w-4" aria-hidden="true" />
          Run Step 1
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-slate-700 px-3 py-2 text-sm text-slate-200"
          onClick={() => onChange({ extractionMode: "automatic", textFixerEnabled: true })}
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Reset
        </button>
      </div>
    </section>
  );
}
