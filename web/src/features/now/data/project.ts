import type { NowModel, NowRun } from "../model";
import type { NowPayload } from "./schema";

export function project(payload: NowPayload): NowModel {
  const runs: NowRun[] = payload.runs.map((summary) => ({
    id: summary.id,
    objective: summary.objective || summary.id,
    repository: summary.repository || "Repository unavailable",
    client: summary.client || undefined,
    lastActivity: summary.last_activity || "Activity unavailable",
    tickets: summary.tickets,
    unreadable: summary.unreadable || (!summary.tickets.length && summary.ticket_count > 0),
  }));
  return { runs };
}
