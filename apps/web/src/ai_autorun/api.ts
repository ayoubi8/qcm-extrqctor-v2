import { actionAiAutoRun, startAiAutoRun, type AiAutoRunPageInput } from "../api/client";
import type { AiAutoRunAction, AiAutoRunDraft } from "./types";

export function startAiAutoRunDraft(userId: string, projectId: string, runId: string, draft: AiAutoRunDraft) {
  const pages: AiAutoRunPageInput[] = [
    { page_number: 1, text: "question page preview" },
    { page_number: 2, text: "correction page preview" }
  ];
  return startAiAutoRun(
    {
      userId,
      projectId,
      runId,
      aiRunId: draft.aiRunId,
      pages,
      modelSelection: {
        provider: "openrouter",
        primary_model_id: draft.primaryModelId,
        fallback_model_ids: draft.fallbackModelIds
      },
      userConstraints: {
        template_name: draft.templateName,
        correction_mode: draft.correctionMode
      },
      idempotencyKey: `${projectId}:${runId}:${draft.aiRunId}`
    },
    `ai-autorun:${draft.aiRunId}`
  );
}

export function controlAiAutoRunDraft(userId: string, projectId: string, aiRunId: string, action: AiAutoRunAction) {
  return actionAiAutoRun(projectId, aiRunId, action, userId, `ai-autorun:${aiRunId}:${action}`);
}
