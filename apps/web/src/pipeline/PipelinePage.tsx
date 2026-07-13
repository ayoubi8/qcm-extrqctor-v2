import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchProjectSnapshot, fetchSignedUrl } from "../api/client";
import { AiAutoRunWindow, useAiAutoRunStore } from "../ai_autorun";
import { AutoRunNotification, AutoRunPanel, useManualAutoRunStore } from "../autorun";
import { ProjectShell } from "../components/shell";
import { Button, Card, StatusBadge } from "../components/ui";
import { HistoryRestorePanel, ProjectLauncher, type ProjectHistoryItem } from "../projects";
import { ArtifactViewer, ResultHub, RunSelector, type ArtifactVersionItem } from "../results";
import { ConfigPanel } from "./ConfigPanel";
import { usePipelineUiStore } from "./pipelineStore";
import { pipelineSteps } from "./stepRegistry";
import { StepList } from "./StepList";
import type { PipelineRunContext, PipelineStepId } from "./types";

interface PipelinePageProps {
  userId: string;
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

export function PipelinePage({ userId }: PipelinePageProps) {
  const [projectId, setProjectId] = useState("demo-project");
  const { notice, openPanel } = useManualAutoRunStore();
  const openAiWindow = useAiAutoRunStore((state) => state.openWindow);
  const { activeStepId, selectedRunId, selectedArtifactVersionId, setActiveStep, setSelectedRun, setSelectedArtifactVersion } = usePipelineUiStore();

  const snapshot = useQuery({
    queryKey: ["project-snapshot", projectId, userId],
    queryFn: () => fetchProjectSnapshot(projectId, userId),
    enabled: Boolean(projectId && userId),
    retry: false
  });

  const signedUrl = useMutation({
    mutationFn: (artifactVersionId: string) => fetchSignedUrl(artifactVersionId, `download:${artifactVersionId}`)
  });

  const runs = snapshot.data?.runs ?? [
    { runId: "demo-run", projectId, label: "Latest run", status: "draft", createdAt: "2026-07-13", updatedAt: "2026-07-13" }
  ];
  const effectiveRunId = selectedRunId ?? runs[0]?.runId ?? "demo-run";
  const artifacts = (snapshot.data?.artifacts as ArtifactVersionItem[] | undefined) ?? demoArtifacts;
  const selectedArtifact = artifacts.find((artifact) => artifact.artifactVersionId === selectedArtifactVersionId) ?? artifacts[0] ?? null;
  const context: PipelineRunContext = useMemo(
    () => ({
      userId,
      projectId,
      runId: effectiveRunId,
      sourceArtifactIds: artifacts.map((artifact) => artifact.artifactId)
    }),
    [artifacts, effectiveRunId, projectId, userId]
  );

  const handleRunStep = (stepId: PipelineStepId, payload: Record<string, unknown>) => {
    setActiveStep(stepId);
    console.info("Queued step payload", payload);
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
          <ProjectLauncher onCreate={(draft) => console.info("Create project draft", draft)} />
          <HistoryRestorePanel items={demoHistory} selectedProjectId={projectId} onRestore={setProjectId} />
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
      <AutoRunPanel userId={userId} projectId={projectId} runId={effectiveRunId} />
      <AiAutoRunWindow userId={userId} projectId={projectId} runId={effectiveRunId} />
    </ProjectShell>
  );
}
