import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node
} from "@xyflow/react";
import { AlertTriangle, ArrowLeft, Binary, LockKeyhole, Network, Radio } from "lucide-react";
import { useMemo, useState } from "react";
import type { ExperienceSnapshot } from "../../api/schema";
import type { LocationState } from "../../state/location";
import { SessionAgentNode, type SessionAgentNodeData } from "./SessionAgentNode";
import {
  isSessionDetail,
  SESSION_NODE_ID,
  sessionTopology,
  type SessionTopology,
  type TopologyNode
} from "./topology";
import "./session-graph.css";

const nodeTypes = { sessionAgent: SessionAgentNode };

function connectionFor(nodeId: string, topology: SessionTopology): string {
  if (nodeId === SESSION_NODE_ID) return "topology root";
  return topology.edges.find((edge) => edge.target === nodeId)?.provenance ?? "connection unknown";
}

function topologyLevel(nodeId: string, topology: SessionTopology, seen = new Set<string>()): number {
  if (nodeId === SESSION_NODE_ID || seen.has(nodeId)) return 0;
  seen.add(nodeId);
  const incoming = topology.edges.find((edge) => edge.target === nodeId);
  if (!incoming || incoming.source === SESSION_NODE_ID) return 1;
  return 1 + topologyLevel(incoming.source, topology, seen);
}

function graphNodes(topology: SessionTopology): Node<SessionAgentNodeData>[] {
  const rowsAtDepth = new Map<number, number>();
  return topology.nodes.map((node) => {
    const level = topologyLevel(node.id, topology);
    const row = rowsAtDepth.get(level) ?? 0;
    rowsAtDepth.set(level, row + 1);
    return {
      id: node.id,
      type: "sessionAgent",
      position: { x: 48 + Math.min(level, 3) * 276, y: 48 + row * 132 },
      data: { ...node, connection: connectionFor(node.id, topology) },
      ariaLabel: `Select ${node.kind} ${node.label}, ${node.state}, ${connectionFor(node.id, topology)}`
    };
  });
}

function graphEdges(topology: SessionTopology): Edge[] {
  return topology.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    ariaLabel: `${edge.source} to ${edge.target}: ${edge.provenance}`,
    focusable: true,
    selectable: false,
    animated: false,
    type: "smoothstep",
    className: edge.inferred ? "session-edge session-edge--inferred" : "session-edge"
  }));
}

function selectedNode(topology: SessionTopology, selected: string): TopologyNode {
  return topology.nodes.find((node) => node.id === selected)
    ?? topology.nodes.find((node) => node.kind === "agent" && node.state === "running")
    ?? topology.nodes[0];
}

function EmptySession({ requested }: { requested: string }) {
  return (
    <section className="session-graph-empty" aria-labelledby="session-graph-title">
      <p className="session-graph-eyebrow"><Network aria-hidden="true" /> Session topology</p>
      <h1 id="session-graph-title">Session metadata is unavailable</h1>
      <p>The reader returned no safe topology for <span className="session-graph-mono">{requested || "this session"}</span>.</p>
      <a href="/sessions"><ArrowLeft aria-hidden="true" /> Back to Sessions</a>
    </section>
  );
}

export function SessionGraphView({ snapshot, location }: { snapshot: ExperienceSnapshot; location: LocationState }) {
  const session = isSessionDetail(snapshot.session) ? snapshot.session : null;
  const topology = useMemo(() => session ? sessionTopology(session) : null, [session]);
  const initial = topology?.nodes.find((node) => node.kind === "agent" && node.state === "running")?.id ?? SESSION_NODE_ID;
  const [selection, setSelection] = useState(initial);
  if (!session || !topology) return <EmptySession requested={location.session} />;

  const inspected = selectedNode(topology, selection);
  const nodes = graphNodes(topology).map((node) => ({ ...node, selected: node.id === inspected.id }));
  const edges = graphEdges(topology);
  const inferredCount = topology.edges.filter((edge) => edge.inferred).length;

  return (
    <div className="foundation-view session-graph-view" data-view="session-graph" data-fixture={location.fixture || "live"}>
      {topology.diagnostics.length > 0 && (
        <section className="session-graph-alert" aria-labelledby="session-graph-alert-title">
          <AlertTriangle aria-hidden="true" />
          <div>
            <p id="session-graph-alert-title">Needs attention</p>
            <ul>{topology.diagnostics.map((item) => <li key={item}>{item}</li>)}</ul>
          </div>
        </section>
      )}

      <header className="session-graph-hero">
        <div>
          <a href="/sessions" className="session-graph-back"><ArrowLeft aria-hidden="true" /> Sessions</a>
          <p className="session-graph-eyebrow"><Network aria-hidden="true" /> Session topology</p>
          <h1 id="session-graph-title">{session.title || "Untitled session"}</h1>
          <p className="session-graph-session-id">Session <span>{session.id}</span></p>
        </div>
        <dl className="session-graph-summary" aria-label="Topology summary">
          <div><dt>Agents</dt><dd>{session.agent_count}</dd></div>
          <div><dt>Inferred</dt><dd>{inferredCount}</dd></div>
          <div><dt>Live</dt><dd>{session.agents.filter((agent) => agent.state === "running").length}</dd></div>
        </dl>
      </header>

      <section className="session-graph-layout" aria-labelledby="session-graph-title">
        <article className="session-graph-panel session-graph-panel--map" aria-labelledby="session-map-heading">
          <header className="session-graph-panel__heading">
            <div><p className="session-graph-eyebrow">Canonical structure</p><h2 id="session-map-heading">Agent graph</h2></div>
            <span className="session-graph-live"><Radio aria-hidden="true" /> Read-only live</span>
          </header>
          <div className="session-graph-canvas">
            <ReactFlowProvider>
              <ReactFlow
                aria-label="Session agent topology"
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodeClick={(_, node) => setSelection(node.id)}
                nodesDraggable={false}
                nodesConnectable={false}
                edgesReconnectable={false}
                deleteKeyCode={null}
                fitView
                fitViewOptions={{ padding: 0.18 }}
                minZoom={0.5}
                maxZoom={1.6}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={24} size={1} />
                <MiniMap
                  ariaLabel="Session topology minimap"
                  nodeColor="var(--status-running)"
                  nodeStrokeColor="var(--session-graph-map)"
                  maskColor="var(--session-graph-map)"
                  position="bottom-left"
                  pannable
                  zoomable
                />
                <Controls position="top-left" showInteractive={false} aria-label="Session graph zoom controls" />
              </ReactFlow>
            </ReactFlowProvider>
          </div>
          <footer className="session-graph-legend" aria-label="Edge provenance legend">
            <span><i aria-hidden="true" /> Recorded topology</span>
            <span><i className="is-inferred" aria-hidden="true" /> Inferred or unresolved</span>
          </footer>
        </article>

        <aside className="session-graph-panel session-graph-inspector" aria-labelledby="session-inspector-heading">
          <div className="session-graph-panel__heading">
            <div><p className="session-graph-eyebrow">Inspector evidence</p><h2 id="session-inspector-heading">{inspected.label}</h2></div>
            <Binary aria-hidden="true" />
          </div>
          <dl>
            <div><dt>Kind</dt><dd>{inspected.kind}</dd></div>
            <div><dt>Type</dt><dd>{inspected.type}</dd></div>
            <div><dt>Depth</dt><dd>{inspected.depth}</dd></div>
            <div><dt>Activity</dt><dd><span className={`session-graph-state is-${inspected.state}`}>● {inspected.state}</span></dd></div>
            <div><dt>Evidence</dt><dd>{inspected.evidence}</dd></div>
            <div><dt>Attached by</dt><dd>{connectionFor(inspected.id, topology)}</dd></div>
          </dl>
          <section className="session-graph-history" aria-labelledby="session-history-heading">
            <h3 id="session-history-heading">Historical metadata</h3>
            <span>Last activity identity</span>
            <code>{inspected.modified || "absent"}</code>
          </section>
          <p className="session-graph-privacy"><LockKeyhole aria-hidden="true" /> Topology and safe metadata only. Prompts, tools, output, files, paths, and conversations stay private.</p>
        </aside>
      </section>
    </div>
  );
}

export default SessionGraphView;
