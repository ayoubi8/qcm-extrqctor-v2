import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createProject, fetchProjectSnapshot, fetchSignedUrl, initializeUpload } from "../api/client";
import { AiAutoRunWindow, useAiAutoRunStore } from "../ai_autorun";
import { AutoRunNotification, AutoRunPanel, useManualAutoRunStore } from "../autorun";
import { ProjectShell } from "../components/shell";
import { Button, Card, StatusBadge } from "../components/ui";
import { HistoryRestorePanel, ProjectLauncher, type ProjectHistoryItem } from "../projects";
import { ArtifactViewer, ResultHub, RunSelector, type ArtifactVersionItem } from "../results";
import { ConfigPanel } from "./ConfigPanel";
import { usePipelineUiStore } from "./pipelineStore";
import { runStep1 } from "./step1/api";
import type { Step1Config } from "./step1/types";
import { runCombinedStep2 } from "./step2/api";
import type { Step2Config } from "./step2/types";
import { runStep3Correction } from "./step3-correction/api";
import type { Step3CorrectionConfig } from "./step3-correction/types";
import { runStep4Similarity } from "./step4-similarity/api";
import type { Step4SimilarityConfig } from "./step4-similarity/types";
import { pipelineSteps } from "./stepRegistry";
import { StepList } from "./StepList";
import type { PipelineRunContext, PipelineStepId } from "./types";
import type { ProjectDraft } from "../projects/types";

interface PipelinePageProps {
  projectId: string;
  onProjectChange: (projectId: string) => void;
}

const demoHistory: ProjectHistoryItem[] = [
  {
    projectId: "demo-project",
    name: "Demo QCM workspace",
    status: "active",
    updatedAt: "2026-07-13",
    latestRunId: "demo-run",
    artifactCount: 4
  }
];

const demoArtifacts: ArtifactVersionItem[] = [
  {
    artifactVersionId: "demo-step1-v1",
    artifactId: "demo-step1",
    artifactType: "step1_text",
    filename: "step1-text.txt",
    contentType: "text/plain",
    versionNumber: 1,
    createdAt: "2026-07-13",
    sizeBytes: 2048,
    runId: "demo-run"
  },
  {
    artifactVersionId: "demo-step2-v1",
    artifactId: "demo-step2",
    artifactType: "step2_final_json",
    filename: "step2-final.json",
    contentType: "application/json",
    versionNumber: 1,
    createdAt: "2026-07-13",
    sizeBytes: 8192,
    runId: "demo-run"
  }
];

export function PipelinePage({ projectId, onProjectChange }: PipelinePageProps) {
  const queryClient = useQueryClient();
  const { notice, openPanel } = useManualAutoRunStore();
  const openAiWindow = useAiAutoRunStore((state) => state.openWindow);
  const { activeStepId, selectedRunId, selectedArtifactVersionId, setActiveStep, setSelectedRun, setSelectedArtifactVersion } = usePipelineUiStore();

  const snapshot = useQuery({
    queryKey: ["project-snapshot", projectId],
    queryFn: () => fetchProjectSnapshot(projectId),
    enabled: Boolean(projectId),
    retry: false
  });

  const signedUrl = useMutation({
    mutationFn: (artifactVersionId: string) => fetchSignedUrl(artifactVersionId, `download:${artifactVersionId}`)
  });
  const createProjectMutation = useMutation({
    mutationFn: async (draft: ProjectDraft) => {
      const created = await createProject(
        {
          name: draft.name,
          idempotencyKey: `project:${draft.name}`
        },
        `project-create:${Date.now()}`
      );
      if (draft.file) {
        await initializeUpload({
          projectId: created.project_id,
          filename: draft.file.name,
          contentType: draft.file.type || "application/pdf",
          sizeBytes: draft.file.size,
          idempotencyKey: `upload:${created.project_id}:${draft.file.name}:${draft.file.size}`
        });
      }
      return created;
    },
    onSuccess: async (created) => {
      onProjectChange(created.project_id);
      setSelectedRun("demo-run");
      await queryClient.invalidateQueries({ queryKey: ["project-snapshot", created.project_id] });
      await queryClient.invalidateQueries({ queryKey: ["terminal", created.project_id] });
    }
  });
  const runStepMutation = useMutation({
    mutationFn: async ({ stepId, payload }: { stepId: PipelineStepId; payload: Record<string, unknown> }) => {
      const correlationId = `${stepId}:${Date.now()}`;
      if (stepId === "step1") {
        return runStep1(
          {
            projectId,
            runId: effectiveRunId,
            sourceFileId: artifacts[0]?.artifactId ?? "demo-source-file",
            sourceFilename: artifacts[0]?.filename ?? "source.pdf",
            config: payload.config as Step1Config,
            idempotencyKey: `${projectId}:${effectiveRunId}:step1:${Date.now()}`
          },
          correlationId
        );
      }
      if (stepId === "step2") {
        return runCombinedStep2(
          {
            projectId,
            runId: effectiveRunId,
            step1ArtifactIds: artifacts.map((artifact) => artifact.artifactId),
            pages: [{ pageNumber: 1, text: "Queued from deployed workspace", sourceArtifactId: artifacts[0]?.artifactId }],
            config: payload.config as Step2Config,
            idempotencyKey: `${projectId}:${effectiveRunId}:step2:${Date.now()}`
          },
          correlationId
        );
      }
      if (stepId === "step3-correction") {
        return runStep3Correction(
          {
            projectId,
            runId: effectiveRunId,
            step2ArtifactIds: artifacts.map((artifact) => artifact.artifactId),
            qcms: [],
            pages: [{ pageNumber: 1, text: "Queued from deployed workspace", sourceArtifactId: artifacts[0]?.artifactId }],
            config: payload.config as Step3CorrectionConfig,
            idempotencyKey: `${projectId}:${effectiveRunId}:step3-correction:${Date.now()}`
          },
          correlationId
        );
      }
      return runStep4Similarity(
        {
          projectId,
          runId: effectiveRunId,
          sourceArtifactIds: artifacts.map((artifact) => artifact.artifactId),
          sourceQcms: [],
          referenceQcms: [],
          existingMatches: [],
          config: payload.config as Step4SimilarityConfig,
          idempotencyKey: `${projectId}:${effectiveRunId}:step4-similarity:${Date.now()}`
        },
        correlationId
      );
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["project-snapshot", projectId] });
      await queryClient.invalidateQueries({ queryKey: ["terminal", projectId] });
    }
  });

  const runs = snapshot.data?.runs ?? [
    { runId: "demo-run", projectId, label: "Latest run", status: "draft", createdAt: "2026-07-13", updatedAt: "2026-07-13" }
  ];
  const effectiveRunId = selectedRunId ?? runs[0]?.runId ?? "demo-run";
  const artifacts = (snapshot.data?.artifacts as ArtifactVersionItem[] | undefined) ?? demoArtifacts;
  const selectedArtifact = artifacts.find((artifact) => artifact.artifactVersionId === selectedArtifactVersionId) ?? artifacts[0] ?? null;
  const context: PipelineRunContext = useMemo(
    () => ({
      projectId,
      runId: effectiveRunId,
      sourceArtifactIds: artifacts.map((artifact) => artifact.artifactId)
    }),
    [artifacts, effectiveRunId, projectId]
  );

  const handleRunStep = (stepId: PipelineStepId, payload: Record<string, unknown>) => {
    setActiveStep(stepId);
    runStepMutation.mutate({ stepId, payload });
  };

  return (
    <ProjectShell
      title={snapshot.data?.project.name ?? "Demo QCM workspace"}
      subtitle="Create, restore, run, inspect artifacts, and recover state from server snapshots."
      status={snapshot.isError ? "offline preview" : snapshot.data?.project.status ?? "draft"}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="primary" onClick={openPanel}>
            Auto Run
          </Button>
          <Button variant="secondary" onClick={openAiWindow}>
            AI Auto Run
          </Button>
          <StatusBadge tone={snapshot.isFetching ? "warning" : "success"}>{snapshot.isFetching ? "syncing" : "reconciled"}</StatusBadge>
        </div>
      }
    >
      <div className="mb-4">
        <AutoRunNotification notice={notice} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)_360px]">
        <div className="grid content-start gap-4">
          <ProjectLauncher onCreate={(draft) => createProjectMutation.mutate(draft)} />
          <HistoryRestorePanel items={demoHistory} selectedProjectId={projectId} onRestore={onProjectChange} />
        </div>

        <div className="grid content-start gap-4">
          <Card title="Visible pipeline" actions={<StatusBadge tone="info">server state</StatusBadge>}>
            <StepList steps={pipelineSteps} activeStepId={activeStepId} onSelect={setActiveStep} />
          </Card>
          <Card title="Step configuration">
            <ConfigPanel activeStepId={activeStepId} context={context} onRunStep={handleRunStep} />
          </Card>
        </div>

        <div className="grid content-start gap-4">
          <Card title="Run selector">
            <RunSelector runs={runs} selectedRunId={effectiveRunId} onSelect={setSelectedRun} />
          </Card>
          <ResultHub artifacts={artifacts} selectedArtifactVersionId={selectedArtifact?.artifactVersionId ?? null} onSelectArtifact={setSelectedArtifactVersion} />
          <ArtifactViewer artifact={selectedArtifact} onDownload={(artifactVersionId) => signedUrl.mutate(artifactVersionId)} />
          {signedUrl.data ? (
            <Card title="Signed URL">
              <p className="break-all text-xs text-cyan-200">{signedUrl.data.signed_url}</p>
            </Card>
          ) : null}
          <Button variant="ghost" onClick={() => snapshot.refetch()}>
            Refresh snapshot
          </Button>
        </div>
      </div>
      <AutoRunPanel projectId={projectId} runId={effectiveRunId} />
      <AiAutoRunWindow projectId={projectId} runId={effectiveRunId} />
    </ProjectShell>
  );
}