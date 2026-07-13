import { Bot, Minimize2, Play, RotateCcw, Square, X } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { Button, Card, TextInput } from "../components/ui";
import { controlAiAutoRunDraft, startAiAutoRunDraft } from "./api";
import { useAiAutoRunStore } from "./aiAutoRunStore";

interface AiAutoRunWindowProps {
  userId: string;
  projectId: string;
  runId: string;
}

export function AiAutoRunWindow({ userId, projectId, runId }: AiAutoRunWindowProps) {
  const { window, draft, closeWindow, toggleMinimized, setDraft } = useAiAutoRunStore();
  const start = useMutation({ mutationFn: () => startAiAutoRunDraft(userId, projectId, runId, draft) });
  const action = useMutation({
    mutationFn: (next: "retry" | "cancel" | "continue") => controlAiAutoRunDraft(userId, projectId, draft.aiRunId, next)
  });

  if (!window.open) {
    return null;
  }

  return (
    <section className="fixed bottom-4 right-4 z-50 w-[min(420px,calc(100vw-32px))] rounded-lg border border-cyan-400/40 bg-slate-950 shadow-2xl">
      <header className="flex min-h-12 items-center justify-between gap-2 border-b border-slate-800 px-3">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-cyan-300" aria-hidden="true" />
          <h2 className="text-sm font-semibold">AI Auto Run</h2>
        </div>
        <div className="flex items-center gap-1">
          <button type="button" className="rounded p-2 text-slate-400 hover:bg-slate-900" onClick={toggleMinimized} aria-label="Minimize AI Auto Run">
            <Minimize2 className="h-4 w-4" aria-hidden="true" />
          </button>
          <button type="button" className="rounded p-2 text-slate-400 hover:bg-slate-900" onClick={closeWindow} aria-label="Close AI Auto Run">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </header>
      {!window.minimized ? (
        <div className="grid gap-3 p-3">
          <Card title="Planner">
            <div className="grid gap-3">
              <TextInput
                label="Primary model"
                value={draft.primaryModelId}
                onChange={(event) => setDraft({ ...draft, primaryModelId: event.target.value })}
              />
              <TextInput
                label="Template"
                value={draft.templateName}
                onChange={(event) => setDraft({ ...draft, templateName: event.target.value })}
              />
              <select
                className="min-h-10 rounded-md border border-slate-700 bg-slate-950 px-3 text-sm"
                value={draft.correctionMode}
                onChange={(event) => setDraft({ ...draft, correctionMode: event.target.value as typeof draft.correctionMode })}
              >
                <option value="page_detection">page_detection</option>
                <option value="vision">vision</option>
                <option value="auto_detection">auto_detection</option>
              </select>
            </div>
          </Card>
          <div className="rounded-md border border-slate-800 bg-slate-900 p-3 text-xs leading-5 text-slate-400">
            AI summaries show evidence only. Raw private reasoning is never displayed.
          </div>
          {start.data ? <div className="rounded-md border border-emerald-400/40 bg-emerald-500/10 p-3 text-sm text-emerald-100">AI Auto Run queued</div> : null}
          {start.isError ? <div className="rounded-md border border-red-400/40 bg-red-500/10 p-3 text-sm text-red-100">AI Auto Run could not start</div> : null}
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" icon={<Play className="h-4 w-4" aria-hidden="true" />} onClick={() => start.mutate()}>
              Launch
            </Button>
            <Button variant="secondary" icon={<RotateCcw className="h-4 w-4" aria-hidden="true" />} onClick={() => action.mutate("retry")}>
              Retry
            </Button>
            <Button variant="danger" icon={<Square className="h-4 w-4" aria-hidden="true" />} onClick={() => action.mutate("cancel")}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
