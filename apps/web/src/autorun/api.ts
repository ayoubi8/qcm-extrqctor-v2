import { controlManualAutoRun, startManualAutoRun, validateManualAutoRun, type ManualAutoRunSnapshot } from "../api/client";
import type { ManualAutoRunControlAction, ManualAutoRunDraft } from "./types";

export function toManualAutoRunSnapshot(draft: ManualAutoRunDraft): ManualAutoRunSnapshot {
  return {
    schema_version: "manual-autorun.v1",
    selected_steps: draft.selectedSteps.map((step) => ({
      step_key: step.stepKey,
      task_kind: step.taskKind,
      enabled: step.enabled,
      config: step.config
    })),
    saved_defaults: draft.saveAsDefaults ? { save_as_defaults: true } : {},
    project_overrides: draft.projectOverrides,
    resource_limits: draft.resourceLimits
  };
}

export function validateManualAutoRunDraft(projectId: string, draft: ManualAutoRunDraft) {
  return validateManualAutoRun(projectId, toManualAutoRunSnapshot(draft));
}

export function startManualAutoRunDraft(userId: string, projectId: string, runId: string, draft: ManualAutoRunDraft) {
  return startManualAutoRun(
    {
      userId,
      projectId,
      runId,
      autoRunId: draft.autoRunId,
      snapshot: toManualAutoRunSnapshot(draft),
      idempotencyKey: `${projectId}:${runId}:${draft.autoRunId}`
    },
    `manual-autorun:${draft.autoRunId}`
  );
}

export function controlManualAutoRunDraft(
  userId: string,
  projectId: string,
  autoRunId: string,
  action: ManualAutoRunControlAction
) {
  return controlManualAutoRun(projectId, autoRunId, action, userId, `manual-autorun:${autoRunId}:${action}`);
}
