import { create } from "zustand";
import type { AiAutoRunDraft, AiAutoRunWindowState } from "./types";

interface AiAutoRunUiState {
  window: AiAutoRunWindowState;
  draft: AiAutoRunDraft;
  openWindow: () => void;
  closeWindow: () => void;
  toggleMinimized: () => void;
  setDraft: (draft: AiAutoRunDraft) => void;
}

export const defaultAiAutoRunDraft: AiAutoRunDraft = {
  aiRunId: "ai-auto-run-preview",
  primaryModelId: "configured-by-admin",
  fallbackModelIds: [],
  templateName: "default",
  correctionMode: "page_detection"
};

export const useAiAutoRunStore = create<AiAutoRunUiState>((set) => ({
  window: { open: false, minimized: false },
  draft: defaultAiAutoRunDraft,
  openWindow: () => set({ window: { open: true, minimized: false } }),
  closeWindow: () => set({ window: { open: false, minimized: false } }),
  toggleMinimized: () => set((state) => ({ window: { ...state.window, minimized: !state.window.minimized } })),
  setDraft: (draft) => set({ draft })
}));
