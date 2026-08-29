import { describe, expect, it } from "vitest";
import { sessionTopology, type SessionDetail } from "./topology";

function session(agents: SessionDetail["agents"]): SessionDetail {
  return {
    id: "session-safe",
    title: "Safe topology",
    modified: "123",
    agent_count: agents.length,
    diagnostics: [],
    agents
  };
}

function agent(id: string, depth: number | null, parent = ""): SessionDetail["agents"][number] {
  return {
    id, type: "orch-worker", depth, parent, modified: "456",
    state: "unknown", evidence: "no call in this transcript", unreadable: false
  };
}

describe("session topology", () => {
  it("preserves canonical parent edges and labels their provenance", () => {
    const topology = sessionTopology(session([
      agent("agent-first", 1),
      agent("agent-child", 2, "first")
    ]));

    expect(topology.edges).toEqual([
      expect.objectContaining({ source: "session-root", target: "agent-first", provenance: "spawn depth 1", inferred: false }),
      expect.objectContaining({ source: "agent-first", target: "agent-child", provenance: "recorded parent", inferred: false })
    ]);
  });

  it("keeps absent and unresolved parents explicit instead of inventing lineage", () => {
    const topology = sessionTopology(session([
      agent("agent-orphan", 3),
      agent("agent-stranger", 2, "missing-parent")
    ]));

    expect(topology.edges.map((edge) => edge.provenance)).toEqual([
      "inferred: no parent recorded",
      "inferred: recorded parent unresolved"
    ]);
    expect(topology.edges.every((edge) => edge.inferred)).toBe(true);
    expect(topology.diagnostics.join(" ")).toMatch(/could not be resolved/i);
    expect(topology.diagnostics.join(" ")).toMatch(/not recorded/i);
  });

  it("leaves unreadable activity unknown and names the diagnostic", () => {
    const unreadable = { ...agent("agent-unreadable", null), unreadable: true, state: "running", evidence: "claimed" };
    const topology = sessionTopology(session([unreadable]));
    expect(topology.nodes[1]).toMatchObject({ state: "unknown", evidence: "metadata unreadable" });
    expect(topology.diagnostics).toContain("Unreadable subagent metadata remains unknown.");
  });
});
