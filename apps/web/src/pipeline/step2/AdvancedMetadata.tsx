import type { Step2Config } from "./types";

interface AdvancedMetadataProps {
  value: Step2Config;
  onChange: (value: Step2Config) => void;
}

export function AdvancedMetadata({ value, onChange }: AdvancedMetadataProps) {
  return (
    <section className="grid gap-3 border-b border-slate-800 py-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Source"
          value={value.metadataDefaults.source ?? ""}
          onChange={(event) =>
            onChange({
              ...value,
              metadataDefaults: { ...value.metadataDefaults, source: event.target.value }
            })
          }
        />
        <input
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          placeholder="Category"
          value={value.metadataDefaults.category ?? ""}
          onChange={(event) =>
            onChange({
              ...value,
              metadataDefaults: { ...value.metadataDefaults, category: event.target.value }
            })
          }
        />
        <select
          className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          value={value.legacySubcategoryPolicy}
          onChange={(event) =>
            onChange({
              ...value,
              legacySubcategoryPolicy: event.target.value as Step2Config["legacySubcategoryPolicy"]
            })
          }
        >
          <option value="preserve_internal">Preserve internally</option>
          <option value="export">Export legacy subcategory</option>
          <option value="drop">Drop legacy subcategory</option>
        </select>
      </div>
    </section>
  );
}
