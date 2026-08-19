import * as Tabs from "@radix-ui/react-tabs";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
  type NodeChange,
  type Viewport
} from "@xyflow/react";
import { Eye, Radio } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useObserveFeed } from "./feed";
import { layoutSnapshot } from "./layout";

const INITIAL_VIEWPORT: Viewport = { x: 48, y: 48, zoom: 1 };

function FlowCanvas({
  nodes,
  edges,
  selectedId,
  onSelectedId
}: {
  nodes: Node[];
  edges: Edge[];
  selectedId: string | null;
  onSelectedId: (id: string | null) => void;
}) {
  const [viewport, setViewport] = useState(INITIAL_VIEWPORT);
  const selectedNodes = useMemo(
    () => nodes.map((node) => ({ ...node, selected: node.id === selectedId })),
    [nodes, selectedId]
  );
  const onNodesChange = (changes: NodeChange[]) => {
    const selected = changes.find(
      (change): change is Extract<NodeChange, { type: "select" }> =>
        change.type === "select" && change.selected
    );
    if (selected) onSelectedId(selected.id);
  };

  return (
    <ReactFlow
      nodes={selectedNodes}
      edges={edges}
      viewport={viewport}
      onViewportChange={setViewport}
      onNodesChange={onNodesChange}
      nodesDraggable={false}
      nodesConnectable={false}
      edgesReconnectable={false}
      deleteKeyCode={null}
      minZoom={0.4}
      maxZoom={1.8}
      proOptions={{ hideAttribution: true }}
      aria-label="Observe dependency graph"
    >
      <Background gap={24} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export function ObserveApp() {
  const { snapshot, unavailable } = useObserveFeed();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!snapshot) return;
    let current = true;
    void layoutSnapshot(snapshot).then((laidOut) => {
      if (current) setNodes(laidOut);
    });
    return () => {
      current = false;
    };
  }, [snapshot]);

  useEffect(() => {
    if (selectedId && snapshot && !snapshot.nodes.some((node) => node.id === selectedId)) {
      setSelectedId(null);
    }
  }, [selectedId, snapshot]);

  const edges = useMemo<Edge[]>(
    () => snapshot?.edges.map((edge) => ({ ...edge, animated: snapshot.active })) ?? [],
    [snapshot]
  );
  const selected = snapshot?.nodes.find((node) => node.id === selectedId);

  return (
    <Tooltip.Provider delayDuration={300}>
      <main data-mode="observe" className="shell">
        <header className="masthead">
          <div className="brand"><Eye aria-hidden="true" /> orchflows</div>
          <div className="mode"><Radio aria-hidden="true" /> Observe</div>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <span className="read-only" tabIndex={0}>read only</span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content className="tooltip" sideOffset={6}>
                This view cannot start, edit, or delete a run.
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </header>
        <section className="workspace" aria-busy={!snapshot}>
          <aside className="rail">
            <Tabs.Root defaultValue="overview">
              <Tabs.List aria-label="Observe panels">
                <Tabs.Trigger value="overview">Overview</Tabs.Trigger>
                <Tabs.Trigger value="selection">Selection</Tabs.Trigger>
              </Tabs.List>
              <Tabs.Content value="overview">
                <h1>Run map</h1>
                <p>{snapshot ? `revision ${snapshot.revision}` : "Waiting for reader"}</p>
                <p>{snapshot?.nodes.length ?? 0} work items</p>
                {unavailable && <p role="status">Reader unavailable; retrying.</p>}
              </Tabs.Content>
              <Tabs.Content value="selection">
                <h1>Selected work item</h1>
                {selected ? (
                  <dl>
                    <dt>Identity</dt><dd>{selected.id}</dd>
                    <dt>Status</dt><dd>{selected.status}</dd>
                  </dl>
                ) : <p>Use the keyboard or pointer to select a node.</p>}
              </Tabs.Content>
            </Tabs.Root>
          </aside>
          <section className="canvas" aria-label="Run map canvas" data-editing="disabled">
            <ReactFlowProvider>
              <FlowCanvas
                nodes={nodes}
                edges={edges}
                selectedId={selectedId}
                onSelectedId={setSelectedId}
              />
            </ReactFlowProvider>
          </section>
        </section>
      </main>
    </Tooltip.Provider>
  );
}
