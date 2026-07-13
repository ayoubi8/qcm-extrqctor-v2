import { Pause, Play, RotateCcw, Square } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { Button, Card } from "../components/ui";
import { controlManualAutoRunDraft, startManualAutoRunDraft, validateManualAutoRunDraft } from "./api";
import { useManualAutoRunStore } from "./autorunStore";

interface AutoRunPanelProps {
  userId: string;
  projectId: string;
  runId: string;
}

export function AutoRunPanel({ userId, projectId, runId }: AutoRunPanelProps) {
  const { panelOpen, draft, closePanel, setDraft, setNotice } = useManualAutoRunStore();
  const validate = useMutation({ mutationFn: () => validateManualAutoRunDraft(projectId, draft) });
  const start = useMutation({
    mutationFn: () => startManualAutoRunDraft(userId, projectId, runId, draft),
    onSuccess: () => {
      setNotice({ tone: "success", message: "Manual Auto Run started" });
      closePanel();
    },
    onError: () => setNotice({ tone: "danger", message: "Manual Auto Run could not start" })
  });
  const control = useMutation({
    mutationFn: (action: "pause" | "resume" | "retry" | "cancel") =>
      controlManualAutoRunDraft(userId, projectId, draft.autoRunId, action)
  });

  if (!panelOpen) {
    return null;
  }

  return (
    <aside className="fixed inset-y-0 right-0 z-40 grid w-full max-w-md grid-rows-[auto_1fr_auto] border-l border-slate-800 bg-slate-950 shadow-2xl">
      <header className="border-b border-slate-800 p-4">
        <h2 className="text-base font-semibold text-slate-100">Manual Auto Run</h2>
        <p className="mt-1 text-sm text-slate-500">Sequentially run selected visible pipeline steps.</p>
      </header>
      <div className="overflow-y-auto p-4">
        <Card title="Steps">
          <div className="grid gap-3">
            {draft.selectedSteps.map((step) => (
              <label key={step.stepKey} className="flex items-center justify-between gap-3 rounded-md border border-slate-800 bg-slate-950 p-3 text-sm">
                <span>
                  <span className="block font-medium text-slate-100">{step.stepKey}</span>
                  <span className="text-xs text-slate-500">{step.taskKind}</span>
                </span>
                <input
                  type="checkbox"
                  checked={step.enabled}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      selectedSteps: draft.selectedSteps.map((item) =>
                        item.stepKey === step.stepKey ? { ...item, enabled: event.target.checked } : item
                      )
                    })
                  }
                />
              </label>
            ))}
          </div>
        </Card>
        <label className="mt-4 flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={draft.saveAsDefaults}
            onChange={(event) => setDraft({ ...draft, saveAsDefaults: event.target.checked })}
          />
          Save selected values as defaults
        </label>
        {validate.data ? (
          <div className="mt-4 rounded-md border border-slate-800 bg-slate-900 p-3 text-sm text-slate-300">
            {validate.data.valid ? "Configuration is valid" : validate.data.errors.join("; ")}
          </div>
        ) : null}
      </div>
      <footer className="flex flex-wrap gap-2 border-t border-slate-800 p-4">
        <Button variant="secondary" onClick={() => validate.mutate()}>
          Validate
        </Button>
        <Button variant="primary" icon={<Play className="h-4 w-4" aria-hidden="true" />} onClick={() => start.mutate()}>
          Start
        </Button>
        <Button variant="ghost" icon={<Pause className="h-4 w-4" aria-hidden="true" />} onClick={() => control.mutate("pause")}>
          Pause
        </Button>
        <Button variant="ghost" icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />} onClick={() => control.mutate("retry")}>
          Retry
        </Button>
        <Button variant="danger" icon={<Square className="h-4 w-4" aria-hidden="true" />} onClick={() => control.mutate("cancel")}>
          Cancel
        </Button>
        <Button variant="ghost" onClick={closePanel}>
          Close
        </Button>
      </footer>
    </aside>
  );
}
