import type { TerminalPage } from "./types";
import { fetchTerminalPage as fetchTerminalPageFromClient } from "../api/client";

export async function fetchTerminalPage(
  projectId: string,
  afterSequence?: number | null
): Promise<TerminalPage> {
  return fetchTerminalPageFromClient(projectId, afterSequence);
}