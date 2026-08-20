import { describe, expect, it, vi } from "vitest";
import {
  createPollingTransport,
  type TransportEnvironment,
} from "../../../shared/transport";
import type { FeatureState } from "../../../shared/transport/types";
import type { WorkflowDetailModel } from "../model";
import type { WorkflowDetailRoute } from "../route";
import type { WorkflowDetailPayload } from "../data/schema";
import {
  catalogData,
  catalogPolling,
  detailData,
  detailPolling,
  sourceData,
  sourcePolling,
} from "../data/useFeed";

const summary = {
  nodes: [{ id: "start", label: "Start" }],
  edges: [{ source: "start", target: "start", kind: "loop" }],
};

const catalogPayload = {
  schema: "orchflows.workflow-catalog.v1",
  workflows: [
    {
      id: "evolve",
      type: "composition",
      entry: "named",
      description: "Run bounded generations.",
      summary,
    },
    {
      id: "orch-spec",
      type: "workflow-skill",
      entry: "callable",
      description: "Shape one delivery run.",
      summary: { nodes: [], edges: [] },
    },
  ],
};

const detailPayload = {
  schema: "orchflows.workflow-detail.v1",
  id: "evolve",
  type: "composition",
  nodes: [
    {
      id: "workflow:evolve",
      kind: "workflow",
      label: "evolve",
      source_id: "src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    },
    { id: "skill:missing", kind: "skill", label: "missing" },
  ],
  edges: [
    {
      id: "edge:executor:workflow%3Aevolve:skill%3Amissing",
      kind: "executor",
      from: "workflow:evolve",
      to: "skill:missing",
      label: "executes with",
    },
  ],
  relations: [
    {
      id: "edge:executor:workflow%3Aevolve:skill%3Amissing",
      kind: "executor",
      from: "workflow:evolve",
      to: "skill:missing",
      label: "executes with",
    },
  ],
  diagnostics: [
    {
      code: "unresolved-reference",
      subject_id: "skill:missing",
      message: "The referenced skill is unavailable.",
    },
  ],
};

const sourcePayload = {
  schema: "orchflows.workflow-source.v1",
  id: "src_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  text: "# evolve\n",
  sha256: "a".repeat(64),
  language: "markdown",
  redacted: false,
};

function response(status: number, value?: unknown): Response {
  return new Response(value === undefined ? null : JSON.stringify(value), {
    status,
    headers: value === undefined ? undefined : { "Content-Type": "application/json" },
  });
}

function environment(fetcher: TransportEnvironment["fetcher"]): TransportEnvironment & {
  scheduled: Array<{ callback: () => void; delay: number }>;
} {
  const scheduled: Array<{ callback: () => void; delay: number }> = [];
  return {
    fetcher,
    scheduled,
    schedule(callback, delay) {
      scheduled.push({ callback, delay });
      return callback;
    },
    cancel: vi.fn(),
  };
}

describe("workflow data contracts", () => {
  it("binds each route to its matching request and closed payload schema", () => {
    expect(catalogData.request({ fixture: "empty" })).toEqual({ url: "/api/v1/workflows" });
    expect(detailData.request({ workflowId: "owner/name ?#%", fixture: "complex" })).toEqual({
      url: "/api/v1/workflows/owner%2Fname%20%3F%23%25",
    });
    expect(sourceData.request({
      workflowId: "owner/name ?#%",
      sourceId: "src_a/b ?#%",
      fixture: "unreadable",
    })).toEqual({
      url: "/api/v1/workflows/owner%2Fname%20%3F%23%25/sources/src_a%2Fb%20%3F%23%25",
    });

    expect(() => catalogData.schema(detailPayload)).toThrow("invalid workflow catalog payload");
    expect(() => detailData.schema(sourcePayload)).toThrow("invalid workflow detail payload");
    expect(() => sourceData.schema(catalogPayload)).toThrow("invalid workflow source payload");

    expect(() => catalogData.schema({ ...catalogPayload, extra: true })).toThrow();
    expect(() => catalogData.schema({
      ...catalogPayload,
      workflows: [{ ...catalogPayload.workflows[0], extra: true }],
    })).toThrow();
    expect(() => catalogData.schema({
      ...catalogPayload,
      workflows: [{
        ...catalogPayload.workflows[0],
        summary: { ...summary, nodes: [{ ...summary.nodes[0], extra: true }] },
      }],
    })).toThrow();
    expect(() => detailData.schema({
      ...detailPayload,
      edges: [{ ...detailPayload.edges[0], extra: true }],
    })).toThrow();
    expect(() => sourceData.schema({ ...sourcePayload, path: "C:/secret" })).toThrow();
  });

  it("projects type-correlated T3 and T1 discriminated models", () => {
    const catalog = catalogData.project(catalogData.schema(catalogPayload));
    expect(catalog.workflows).toEqual([
      expect.objectContaining({ id: "evolve", type: "composition", tier: "T3", entry: "named" }),
      expect.objectContaining({ id: "orch-spec", type: "workflow-skill", tier: "T1", entry: "callable" }),
    ]);

    const detail = detailData.project(detailData.schema(detailPayload));
    expect(detail).toMatchObject({ id: "evolve", type: "composition", tier: "T3" });
    expect(detail.nodes[0]).toEqual(expect.objectContaining({
      id: "workflow:evolve",
      sourceId: sourcePayload.id,
    }));
    expect(detail.nodes[1]).not.toHaveProperty("sourceId");
    expect(detail.diagnostics[0]).toEqual(expect.objectContaining({
      code: "unresolved-reference",
      subjectId: "skill:missing",
    }));
    expect(detailData.project(detailData.schema({
      ...detailPayload,
      id: "orch-spec",
      type: "workflow-skill",
    }))).toMatchObject({ id: "orch-spec", type: "workflow-skill", tier: "T1" });

    const source = sourceData.project(sourceData.schema(sourcePayload));
    expect(source).toEqual(sourcePayload);

    expect(() => catalogData.schema({
      ...catalogPayload,
      workflows: [{ ...catalogPayload.workflows[0], entry: "callable" }],
    })).toThrow();
  });

  it("uses definition polling for list/detail and keeps inert source text unpolled", () => {
    expect(catalogPolling(null)).toEqual({ intervalMs: 5000 });
    expect(detailPolling(null)).toEqual({ intervalMs: 5000 });
    expect(sourcePolling(null)).toBe(false);
  });
});

describe("workflow shared-transport lifecycle", () => {
  it("invalidates an older route generation before it can overwrite a newer detail", async () => {
    let resolveOld!: (value: Response) => void;
    let resolveNew!: (value: Response) => void;
    const oldResponse = new Promise<Response>((resolve) => { resolveOld = resolve; });
    const newResponse = new Promise<Response>((resolve) => { resolveNew = resolve; });
    const fetcher = vi.fn().mockReturnValueOnce(oldResponse).mockReturnValueOnce(newResponse);
    const states: FeatureState<WorkflowDetailModel>[] = [];
    const transport = createPollingTransport<
      WorkflowDetailRoute,
      WorkflowDetailPayload,
      WorkflowDetailModel
    >({
      environment: environment(fetcher),
      onState: (state: FeatureState<WorkflowDetailModel>) => states.push(state),
    });

    const oldPoll = transport.start({ workflowId: "old", fixture: "" }, detailData);
    const oldSignal = fetcher.mock.calls[0][1]?.signal;
    const newPoll = transport.start({ workflowId: "evolve", fixture: "" }, detailData);

    expect(oldSignal?.aborted).toBe(true);
    resolveNew(response(200, detailPayload));
    await newPoll;
    resolveOld(response(200, { ...detailPayload, id: "old" }));
    await oldPoll;

    expect(states.at(-1)).toMatchObject({ status: "ready", model: { id: "evolve" } });
    expect(states).not.toContainEqual(expect.objectContaining({ model: expect.objectContaining({ id: "old" }) }));
  });

  it("publishes only while mounted and recovers on the next scheduled poll", async () => {
    let resolveStopped!: (value: Response) => void;
    const stoppedResponse = new Promise<Response>((resolve) => { resolveStopped = resolve; });
    const stoppedStates: FeatureState<WorkflowDetailModel>[] = [];
    const stoppedTransport = createPollingTransport<
      WorkflowDetailRoute,
      WorkflowDetailPayload,
      WorkflowDetailModel
    >({
      environment: environment(vi.fn().mockReturnValue(stoppedResponse)),
      onState: (state: FeatureState<WorkflowDetailModel>) => stoppedStates.push(state),
    });
    const stoppedPoll = stoppedTransport.start({ workflowId: "evolve", fixture: "" }, detailData);
    stoppedTransport.stop();
    resolveStopped(response(200, detailPayload));
    await stoppedPoll;
    expect(stoppedStates.map(({ status }) => status)).toEqual(["loading"]);

    const recoveringStates: FeatureState<WorkflowDetailModel>[] = [];
    const env = environment(vi.fn()
      .mockResolvedValueOnce(response(503))
      .mockResolvedValueOnce(response(200, detailPayload)));
    const recoveringTransport = createPollingTransport<
      WorkflowDetailRoute,
      WorkflowDetailPayload,
      WorkflowDetailModel
    >({
      environment: env,
      onState: (state: FeatureState<WorkflowDetailModel>) => recoveringStates.push(state),
    });
    await recoveringTransport.start({ workflowId: "evolve", fixture: "" }, detailData);
    expect(recoveringStates.at(-1)).toMatchObject({ status: "error" });
    expect(env.scheduled.at(-1)?.delay).toBe(5000);

    env.scheduled.at(-1)?.callback();
    await vi.waitFor(() => {
      expect(recoveringStates.at(-1)).toMatchObject({ status: "ready", model: { id: "evolve" } });
    });
  });
});
