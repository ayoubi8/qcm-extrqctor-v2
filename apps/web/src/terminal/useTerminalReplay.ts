import { useQuery } from "@tanstack/react-query";
import { fetchTerminalPage } from "../api/client";
import type { TerminalEvent } from "./types";

export function useTerminalReplay(projectId: string | null, userId: string | null, afterSequence?: number | null) {
  return useQuery({
    queryKey: ["terminal", projectId, userId, afterSequence ?? 0],
    enabled: Boolean(projectId && userId),
    refetchInterval: 5000,
    queryFn: () => fetchTerminalPage(projectId as string, userId as string, afterSequence),
    select: (page) => ({
      events: page.events as TerminalEvent[],
      nextCursor: page.next_cursor
    })
  });
}
