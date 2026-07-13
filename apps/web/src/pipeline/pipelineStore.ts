import { create } from "zustand";
import type { PipelineStepId } from "./types";

interface PipelineUiState {
  activeStepId: PipelineStepId;
  selectedRunId: string | null;
  selectedArtifactVersionId: string | null;
  setActiveStep: (stepId: PipelineStepId) => void;
  setSelectedRun: (runId: string | null) => void;
  setSelectedArtifactVersion: (artifactVersionId: string | null) => void;
}

export const usePipelineUiStore = create<PipelineUiState>((set) => ({
  activeStepId: "step1",
  selectedRunId: null,
  selectedArtifactVersionId: null,
  setActiveStep: (activeStepId) => set({ activeStepId }),
  setSelectedRun: (selectedRunId) => set({ selectedRunId }),
  setSelectedArtifactVersion: (selectedArtifactVersionId) => set({ selectedArtifactVersionId })
}));
