import { defineCatalog, defineFeature } from "../catalog";
import * as friction from "../../features/friction";
import * as inspector from "../../features/inspector";
import * as now from "../../features/now";
import * as runMap from "../../features/run-map";
import * as sessionGraph from "../../features/session-graph";
import * as sessions from "../../features/sessions";

export const featureCatalog = defineCatalog([
  defineFeature({
    kind: "feature",
    id: "now",
    matchPriority: 10,
    navigation: { label: "Now", home: { fixture: "" } },
    activeNavigationId: "now",
    route: now.route,
    data: now.data,
    loadView: now.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "run-map",
    matchPriority: 10,
    navigation: { label: "Workflows", home: { run: "", fixture: "" } },
    activeNavigationId: "workflows",
    route: runMap.route,
    data: runMap.data,
    loadView: runMap.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "ticket",
    matchPriority: 20,
    navigation: false,
    activeNavigationId: "workflows",
    route: inspector.route,
    data: inspector.data,
    loadView: inspector.loadView,
  }),
  {
    kind: "disabled",
    id: "create",
    navigation: {
      label: "Create",
      reason: "Future workflow authoring is unavailable in this read-only observer.",
    },
  },
  defineFeature({
    kind: "feature",
    id: "sessions",
    matchPriority: 10,
    navigation: { label: "Sessions", home: { fixture: "" } },
    activeNavigationId: "sessions",
    route: sessions.route,
    data: sessions.data,
    loadView: sessions.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "session-graph",
    matchPriority: 20,
    navigation: false,
    activeNavigationId: "sessions",
    route: sessionGraph.route,
    data: sessionGraph.data,
    loadView: sessionGraph.loadView,
  }),
  defineFeature({
    kind: "feature",
    id: "friction",
    matchPriority: 10,
    navigation: { label: "Friction", home: { fixture: "" } },
    activeNavigationId: "friction",
    route: friction.route,
    data: friction.data,
    loadView: friction.loadView,
  }),
] as const);
