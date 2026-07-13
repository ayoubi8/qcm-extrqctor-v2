import type { TerminalEvent } from "./types";

const levelClass: Record<string, string> = {
  debug: "text-slate-500",
  info: "text-slate-300",
  warning: "text-amber-300",
  error: "text-red-300",
  success: "text-emerald-300"
};

export function TerminalEventList({ events }: { events: TerminalEvent[] }) {
  return (
    <div className="h-48 overflow-y-auto border-t border-slate-800 bg-slate-950 p-3 font-mono text-xs">
      {events.length === 0 ? (
        <span className="text-slate-500">No terminal events yet.</span>
      ) : (
        events.map((event) => (
          <div key={event.event_id} className="flex gap-3 leading-relaxed">
            <span className="shrink-0 text-slate-600">#{event.sequence}</span>
            <span className={levelClass[event.level] ?? "text-slate-300"}>{event.message}</span>
          </div>
        ))
      )}
    </div>
  );
}
