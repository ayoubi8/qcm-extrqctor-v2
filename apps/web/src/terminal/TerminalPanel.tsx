import { TerminalSquare } from "lucide-react";
import { Card } from "../components/ui";
import { TerminalEventList } from "./TerminalEventList";
import type { TerminalEvent } from "./types";
import { useTerminalReplay } from "./useTerminalReplay";

interface TerminalPanelProps {
  projectId: string | null;
  userId: string | null;
  fallbackEvents?: TerminalEvent[];
}

export function TerminalPanel({ projectId, userId, fallbackEvents = [] }: TerminalPanelProps) {
  const { data, isLoading, isError } = useTerminalReplay(projectId, userId);
  const events = data?.events ?? fallbackEvents;

  return (
    <Card title="Persistent terminal" actions={<TerminalSquare className="h-4 w-4 text-cyan-300" aria-hidden="true" />} className="rounded-none border-x-0 border-b-0">
      {isLoading ? <p className="px-3 pb-2 text-xs text-slate-500">Replaying terminal events...</p> : null}
      {isError ? <p className="px-3 pb-2 text-xs text-amber-300">Terminal replay is using local fallback events.</p> : null}
      <TerminalEventList events={events} />
    </Card>
  );
}
