import { create } from "zustand";
import type { ManualAutoRunDraft, ManualAutoRunNotice } from "./types";

interface ManualAutoRunUiState {
  panelOpen: boolean;
  draft: ManualAutoRunDraft;
  notice: ManualAutoRunNotice | null;
  openPanel: () => void;
  closePanel: () => void;
  setDraft: (draft: ManualAutoRunDraft) => void;
  setNotice: (notice: ManualAutoRunNotice | null) => void;
}

export const defaultManualAutoRunDraft: ManualAutoRunDraft = {
  autoRunId: "manual-auto-run-preview",
  selectedSteps: [
    { stepKey: "step1", taskKind: "step1_extract", enabled: true, config: {} },
    { stepKey: "step2", taskKind: "step2_orchestrate", enabled: true, config: {} },
    { stepKey: "step3-correction", taskKind: "step3_correction", enabled: false, config: {} },
    { stepKey: "step4-similarity", taskKind: "step4_similarity_match", enabled: false, config: {} }
  ],
  saveAsDefaults: false,
  projectOverrides: {},
  resourceLimits: { max_parallel_steps: 1 }
};

export const useManualAutoRunStore = create<ManualAutoRunUiState>((set) => ({
  panelOpen: false,
  draft: defaultManualAutoRunDraft,
  notice: null,
  openPanel: () => set({ panelOpen: true }),
  closePanel: () => set({ panelOpen: false }),
  setDraft: (draft) => set({ draft }),
  setNotice: (notice) => set({ notice })
}));
