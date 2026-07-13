export type TerminalLevel = "debug" | "info" | "warning" | "error" | "success";

export interface TerminalEvent {
  event_id: string;
  sequence: number;
  user_id: string;
  project_id: string;
  run_id?: string | null;
  task_id?: string | null;
  attempt_id?: string | null;
  level: TerminalLevel;
  event_type: string;
  message: string;
  safe_payload: Record<string, unknown>;
  created_at: string;
}

export interface TerminalPage {
  events: TerminalEvent[];
  next_cursor: number | null;
}
