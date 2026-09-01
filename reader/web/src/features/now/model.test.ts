import { describe, expect, it } from "vitest";
import { nowFixture } from "./fixtures";
import {
  blockedBadge, dependencyLayers, groupState, projectFleet, projectGroups, projectWork, runSummary,
} from "./model";

describe("Now fleet projection", () => {
  it("assigns each run exactly once and orders attention, active, completed", () => {
    const runs = nowFixture("mixed-live").runs;
    const fleet = projectFleet([...runs, runs[0]]);
    expect(fleet.map((run) => run.band)).toEqual(["attention", "active", "active", "completed", "completed"]);
    expect(new Set(fleet.map((run) => run.id)).size).toBe(fleet.length);
    expect(projectFleet(nowFixture("needs-attention").runs).map((run) => run.band)).toEqual(["attention", "completed"]);
  });

  it("rolls exact states by frozen precedence", () => {
    const active = nowFixture("mixed-live").runs[1].tickets;
    expect(groupState(active.filter((ticket) => ticket.status === "claimed"))).toBe("running");
    expect(groupState(active.filter((ticket) => ticket.status === "ready"))).toBe("ready");
    expect(groupState(active.filter((ticket) => ticket.status === "pending"))).toBe("waiting");
    expect(groupState(active.filter((ticket) => ticket.status === "complete"))).toBe("complete");
    expect(groupState(nowFixture("needs-attention").runs[0].tickets)).toBe("attention");
    expect(groupState(nowFixture("unreadable-data").runs[0].tickets)).toBe("unknown");
  });

  it("keeps groups reversible with all child ids and real internal edges", () => {
    const tickets = nowFixture("mixed-live").runs[1].tickets;
    const groups = projectGroups(tickets);
    expect(groups.flatMap((group) => group.ticketIds).sort()).toEqual(tickets.map((ticket) => ticket.id).sort());
    const ticketIds = new Set(tickets.map((ticket) => ticket.id));
    for (const group of groups) for (const edge of group.edges) {
      expect(ticketIds.has(edge.source)).toBe(true);
      expect(ticketIds.has(edge.target)).toBe(true);
    }
    expect(projectFleet([nowFixture("mixed-live").runs[1]])[0].path).toContain("Work x3");
  });

  it("keeps malformed topology in a visible unknown layer", () => {
    const run = nowFixture("unreadable-data").runs[0];
    run.tickets[1].depends_on = ["missing-parent"];
    expect(dependencyLayers(run.tickets).flat()).toContain(run.tickets[1].id);
    expect(projectGroups(run.tickets).some((group) => group.state === "unknown")).toBe(true);
  });

  it("names exact current and next tickets without guessing past dependencies", () => {
    const active = projectWork(nowFixture("mixed-live").runs[1].tickets);
    expect(active.current.map((ticket) => ticket.id)).toEqual(["02-now", "03-workflows"]);
    expect(active.next.map((ticket) => ticket.id)).toEqual(["04-sessions"]);

    const attention = projectWork(nowFixture("needs-attention").runs[0].tickets);
    expect(attention.current.map((ticket) => ticket.id)).toEqual(["01-repair"]);
    expect(attention.next).toEqual([]);

    const unknown = projectWork(nowFixture("unreadable-data").runs[0].tickets);
    expect(unknown.unknown.map((ticket) => ticket.id)).toEqual(["01-repair"]);
  });

  it("names the real fan-out/fan-in edge kind between groups instead of hard-coding sequence", () => {
    const run = projectFleet(nowFixture("mixed-live").runs)
      .find((candidate) => candidate.id === "20260819-ui-experience")!;
    const { summary } = runSummary(run);
    expect(summary.nodes.map((node) => node.label)).toEqual(["Brief", "Plan", "Work ×3", "Review", "Verify"]);
    expect(summary.edges.map((edge) => edge.kind)).toEqual(["sequence", "branch", "branch", "sequence"]);
  });

  it("badges only the run whose current work names a live blocking cause and chain", () => {
    const blocked = nowFixture("needs-attention").runs[0].tickets;
    const badge = blockedBadge(blocked);
    expect(badge).toEqual({
      ticketId: "01-repair", cause: "blocked_upstream",
      reason: "blocked by upstream work", blockingTicket: "00-scope",
    });
    expect(blockedBadge(nowFixture("mixed-live").runs[1].tickets)).toBeNull();
    expect(blockedBadge(nowFixture("unreadable-data").runs[0].tickets)).toBeNull();
  });
});
