import { AlertTriangle, CheckCircle2, Circle, Loader2, Lock } from "lucide-react";
import { StatusBadge } from "../components/ui";
import type { PipelineStepId, PipelineStepState, PipelineStepStatus } from "./types";

interface StepListProps {
  steps: PipelineStepState[];
  activeStepId: PipelineStepId;
  onSelect: (stepId: PipelineStepId) => void;
}

const statusIcon: Record<PipelineStepStatus, typeof Circle> = {
  locked: Lock,
  ready: Circle,
  queued: Loader2,
  running: Loader2,
  completed: CheckCircle2,
  warning: AlertTriangle,
  failed: AlertTriangle
};

export function StepList({ steps, activeStepId, onSelect }: StepListProps) {
  return (
    <nav className="grid gap-2" aria-label="Pipeline steps">
      {steps.map((step) => {
        const Icon = statusIcon[step.status];
        const disabled = step.status === "locked";
        return (
          <button
            key={step.id}
            type="button"
            disabled={disabled}
            className={`grid min-h-16 grid-cols-[auto_1fr_auto] items-center gap-3 rounded-md border px-3 text-left transition-colors ${
              activeStepId === step.id ? "border-cyan-400/60 bg-cyan-400/10" : "border-slate-800 bg-slate-950 hover:border-slate-700"
            } disabled:cursor-not-allowed disabled:opacity-60`}
            onClick={() => onSelect(step.id)}
          >
            <Icon className="h-4 w-4 text-cyan-300" aria-hidden="true" />
            <span>
              <span className="block text-sm font-medium text-slate-100">{step.title}</span>
              <span className="text-xs text-slate-500">{step.taskKind}</span>
            </span>
            <StatusBadge tone={step.status === "failed" ? "danger" : step.status === "completed" ? "success" : "neutral"}>{step.status}</StatusBadge>
          </button>
        );
      })}
    </nav>
  );
}
