import { FileSpreadsheet, RotateCcw } from "lucide-react";
import type { Step2Config } from "./types";

interface Step2ConfigPanelProps {
  value: Step2Config;
  onChange: (value: Step2Config) => void;
  onRun: () => void;
}

export function Step2ConfigPanel({ value, onChange, onRun }: Step2ConfigPanelProps) {
  return (
    <section className="grid gap-4 border-b border-slate-800 py-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Template"
          value={value.templateName}
          onChange={(event) => onChange({ ...value, templateName: event.target.value || "default" })}
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Year"
          value={value.metadataDefaults.year ?? ""}
          onChange={(event) =>
            onChange({
              ...value,
              metadataDefaults: { ...value.metadataDefaults, year: event.target.value }
            })
          }
        />
        <select
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={value.outputFormat}
          onChange={(event) => onChange({ ...value, outputFormat: event.target.value as Step2Config["outputFormat"] })}
        >
          <option value="json+xlsx">JSON and XLSX</option>
          <option value="json">JSON only</option>
        </select>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-cyan-300 bg-cyan-300 px-3 py-2 text-sm font-medium text-slate-950"
          onClick={onRun}
        >
          <FileSpreadsheet className="h-4 w-4" aria-hidden="true" />
          Run Step 2
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-2 rounded border border-slate-700 px-3 py-2 text-sm text-slate-200"
          onClick={() =>
            onChange({
              pageBatchSize: 0,
              internalPageConcurrency: 5,
              extractionPromptId: "step2.page_qcm_extraction.v1",
              metadataDefaults: {},
              metadataStrategies: {},
              legacySubcategoryPolicy: "preserve_internal",
              templateName: "default",
              templateOverrides: {},
              outputFormat: "json+xlsx",
              model: { provider: "openrouter", primaryModelId: "configured-by-admin", fallbackModelIds: [] }
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
