import { AuthGate } from "./auth/AuthGate";
import { AppShell } from "./components/shell";
import { PipelinePage } from "./pipeline/PipelinePage";
import { TerminalPanel } from "./terminal/TerminalPanel";
import type { TerminalEvent } from "./terminal/types";
import { useState } from "react";

const terminalEvents: TerminalEvent[] = [
  {
    event_id: "shell-ready",
    sequence: 1,
    user_id: "system",
    project_id: "preview-project",
    level: "success",
    event_type: "system_message",
    message: "Application shell ready",
    safe_payload: {},
    created_at: "2026-07-13T00:00:00Z"
  }
];

function AuthenticatedApp() {
  const [projectId, setProjectId] = useState("demo-project");

  return (
    <AppShell terminal={<TerminalPanel projectId={projectId} fallbackEvents={terminalEvents} />}>
      <PipelinePage projectId={projectId} onProjectChange={setProjectId} />
    </AppShell>
  );
}

export function App() {
  return (
    <AuthGate>
      <AuthenticatedApp />
    </AuthGate>
  );
}