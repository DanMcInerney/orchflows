import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node
} from "@xyflow/react";
import { AlertTriangle, ArrowLeft, Binary, LockKeyhole, Network, Radio } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { FeatureState } from "../../shared/transport/types";
import { SessionAgentNode, type SessionAgentNodeData } from "./SessionAgentNode";
import {
  isSessionDetail,
  SESSION_NODE_ID,
  sessionTopology,
  type SessionGraphModel,
  type SessionTopology,
  type TopologyNode
} from "./topology";
import type { SessionGraphRoute } from "./route";
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

function topologyPositions(topology: SessionTopology): Map<string, { level: number; row: number }> {
  const rowsAtDepth = new Map<number, number>();
  return new Map(topology.nodes.map((node) => {
    const level = topologyLevel(node.id, topology);
    const row = rowsAtDepth.get(level) ?? 0;
    rowsAtDepth.set(level, row + 1);
    return [node.id, { level, row }];
  }));
}

function graphNodes(topology: SessionTopology): Node<SessionAgentNodeData>[] {
  const positions = topologyPositions(topology);
  return topology.nodes.map((node) => {
    const { level, row } = positions.get(node.id) ?? { level: 0, row: 0 };
    return {
      id: node.id,
      type: "sessionAgent",
      position: { x: 48 + level * 236, y: 48 + row * 132 },
      data: { ...node, connection: connectionFor(node.id, topology) },
      ariaLabel: `Select ${node.kind} ${node.label}, ${node.state}, ${connectionFor(node.id, topology)}`
    };
  });
}

function TopologyMiniMap({ topology }: { topology: SessionTopology }) {
  const positions = topologyPositions(topology);
  const point = (id: string) => {
    const { level, row } = positions.get(id) ?? { level: 0, row: 0 };
    return { x: 8 + level * 44, y: 9 + row * 18 };
  };
  return (
    <svg
      className="session-graph-minimap"
      viewBox={`0 0 ${Math.max(...[...positions.values()].map(({ level }) => 8 + level * 44 + 26))} ${Math.max(...[...positions.values()].map(({ row }) => 9 + row * 18 + 18))}`}
      role="img"
      aria-label={`Session topology minimap, ${topology.nodes.length} nodes and ${topology.edges.length} edges`}
    >
      {topology.edges.map((edge) => {
        const source = point(edge.source);
        const target = point(edge.target);
        return (
          <path
            key={edge.id}
            className={edge.inferred ? "is-inferred" : undefined}
            d={`M ${source.x + 18} ${source.y + 5} L ${target.x} ${target.y + 5}`}
          />
        );
      })}
      {topology.nodes.map((node) => {
        const position = point(node.id);
        return (
          <rect
            key={node.id}
            className={node.state === "running" ? "is-running" : undefined}
            x={position.x}
            y={position.y}
            width="18"
            height="10"
            rx="2"
          />
        );
      })}
    </svg>
  );
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

export interface SessionGraphViewProps {
  route: SessionGraphRoute;
  state: FeatureState<SessionGraphModel>;
}

export function SessionGraphView({ route, state }: SessionGraphViewProps) {
  const session = isSessionDetail(state.model?.session) ? state.model.session : null;
  const topology = useMemo(() => session ? sessionTopology(session) : null, [session]);
  const initial = topology?.nodes.find((node) => node.kind === "agent" && node.state === "running")?.id ?? SESSION_NODE_ID;
  const [selection, setSelection] = useState(initial);
  const [showGraph, setShowGraph] = useState(false);
  const [query, setQuery] = useState("");
  const inspector = useRef<HTMLElement>(null);
  const agentList = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!topology || topology.nodes.some((node) => node.id === selection)) return;
    setSelection(selectedNode(topology, selection).id);
    if (document.activeElement === document.body) {
      agentList.current?.querySelector<HTMLButtonElement>('button[aria-pressed="true"]')?.focus();
    }
  }, [topology, selection]);
  const select = (id: string) => {
    setSelection(id);
    inspector.current?.querySelector("h2")?.scrollIntoView?.({ block: window.innerWidth <= 760 ? "start" : "nearest", behavior: "instant" });
  };
  if (!route.fixture && state.status === "loading") return <div className="loading">Waiting for reader</div>;
  if (!route.fixture && state.status === "error") return <div className="notice" role="status">{state.error.message}</div>;
  if (!session || !topology) return <EmptySession requested={route.session} />;

  const inspected = selectedNode(topology, selection);
  const nodes = graphNodes(topology).map((node) => ({ ...node, selected: node.id === inspected.id }));
  const edges = graphEdges(topology);
  const inferredCount = topology.edges.filter((edge) => edge.inferred).length;

  return (
    <div className="foundation-view session-graph-view" data-view="session-graph" data-fixture={route.fixture || "live"}>
      {state.status === "stale" && <div className="notice" role="status">{state.error.message}</div>}
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
          <p className="session-graph-session-id">Agent-session metadata · <span>{session.id}</span></p>
        </div>
        <dl className="session-graph-summary" aria-label="Topology summary">
          <div><dt>Agents</dt><dd>{session.agent_count}</dd></div>
          <div><dt>Inferred</dt><dd>{inferredCount}</dd></div>
          <div><dt>Live</dt><dd>{session.agents.filter((agent) => !agent.unreadable && agent.state === "running").length}</dd></div>
        </dl>
      </header>

      <section className="session-graph-layout" aria-labelledby="session-graph-title">
        <article className="session-graph-panel session-graph-panel--map" aria-labelledby="session-map-heading">
          <header className="session-graph-panel__heading">
            <div><p className="session-graph-eyebrow">Canonical structure</p><h2 id="session-map-heading">Agent graph</h2></div>
            <span className="session-graph-live"><Radio aria-hidden="true" /> Read-only live</span>
          </header>
          <div className="session-agent-overview">
            <p>Agent-session metadata shows discovered agents and their connections. Execution runs are in Now.</p>
            <label>Find an agent<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter identity or type" /></label>
            <div ref={agentList} className="session-agent-list" aria-label="All session agents">
              {topology.nodes.filter((node) => `${node.label} ${node.type}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())).map((node) => (
                <button key={node.id} aria-label={`${node.label}, ${node.type}, ${node.state}`} aria-pressed={node.id === inspected.id} onClick={() => select(node.id)}>
                  <strong>{node.label}</strong><span>{node.type} · {node.state}</span>
                </button>
              ))}
            </div>
            {topology.nodes.every((node) => !`${node.label} ${node.type}`.toLocaleLowerCase().includes(query.toLocaleLowerCase())) && <p role="status">No matching agents. Clear the filter to see all agents.</p>}
            <button className="session-topology-toggle" aria-expanded={showGraph} onClick={() => setShowGraph(!showGraph)}>{showGraph ? "Hide full topology" : `Show full topology (${topology.nodes.length} nodes)`}</button>
          </div>
          {showGraph && <div className="session-graph-canvas" onKeyDownCapture={(event) => {
            if (event.key !== "Enter" && event.key !== " ") return;
            const node = (event.target as HTMLElement).closest<HTMLElement>(".react-flow__node");
            if (!node?.dataset.id) return;
            event.preventDefault();
            event.stopPropagation();
            select(node.dataset.id);
          }}>
            <ReactFlowProvider>
              <ReactFlow
                aria-label="Session agent topology"
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodeClick={(_, node) => select(node.id)}
                nodesDraggable={false}
                nodesConnectable={false}
                edgesReconnectable={false}
                deleteKeyCode={null}
                fitView
                fitViewOptions={{ padding: 0.16, maxZoom: 0.88 }}
                minZoom={0.05}
                maxZoom={1.6}
                proOptions={{ hideAttribution: true }}
              >
                <Background gap={24} size={1} />
                <TopologyMiniMap topology={topology} />
                <Controls position="top-left" showInteractive={false} aria-label="Session graph zoom controls" />
              </ReactFlow>
            </ReactFlowProvider>
          </div>}
          <footer className="session-graph-legend" aria-label="Edge provenance legend">
            <span><i aria-hidden="true" /> Recorded topology</span>
            <span><i className="is-inferred" aria-hidden="true" /> Inferred or unresolved</span>
          </footer>
        </article>

        <aside ref={inspector} className="session-graph-panel session-graph-inspector" aria-labelledby="session-inspector-heading" aria-live="polite">
          <div className="session-graph-panel__heading">
            <div><p className="session-graph-eyebrow">Selected agent details</p><h2 id="session-inspector-heading">{inspected.label}</h2></div>
            <Binary aria-hidden="true" />
          </div>
          <dl>
            <div><dt>Kind</dt><dd>{inspected.kind}</dd></div>
            <div><dt>Type</dt><dd>{inspected.type}</dd></div>
            <div><dt>Depth</dt><dd>{inspected.depth ?? "unknown"}</dd></div>
            <div><dt>Activity</dt><dd><span className={`session-graph-state is-${inspected.state}`}>● {inspected.state}</span></dd></div>
            <div><dt>Evidence</dt><dd>{inspected.evidence}</dd></div>
            <div><dt>Connected to</dt><dd>{topology.nodes.find((node) => node.id === topology.edges.find((edge) => edge.target === inspected.id)?.source)?.label ?? "topology root"}</dd></div>
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
