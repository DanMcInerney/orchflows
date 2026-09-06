/**
 * Native Chrome frame qualification.
 *
 * This is a deliberately small projection of the pinned DevTools
 * FramesHandler (9f9f40ba5bca7e385be30535cdbf01a3a7e5ba44). Meta, Renderer,
 * and LayerTree facts are derived from the trace before the compositor queue
 * is consumed. A canvas layer's existence is only an attribution candidate;
 * native animation also needs a read-only canvas observation taken by the
 * host-owned render-callback seam (or an observed native update marker). This
 * prevents rAF cadence or a static layer from proving presentation.
 */
import {inputError, requireObject, requireString, sha256} from "./_common.mjs";

const DRAW_NAMES = new Set(["drawframe", "draw_frame", "compositelayers", "compositelayerslegacy"]);
const DROP_NAMES = new Set(["droppedframe", "dropped_frame"]);
const IDLE_NAMES = new Set(["idleframe", "idle_frame"]);
const BEGIN_NAMES = new Set(["beginframe", "begin_frame"]);
const PARTIAL_NAMES = new Set(["partialframe", "partial_frame"]);
const MAIN_MARKERS = new Set(["schedulestylerecalculation", "invalidatelayout", "beginmainthreadframe", "scrolllayer"]);
const COMPOSITOR_NAMES = new Set([
  ...DRAW_NAMES, ...DROP_NAMES, ...IDLE_NAMES, ...BEGIN_NAMES,
  "requestmainthreadframe", "activatelayertree", "needsbeginframechanged", "setlayertreeid", "commit",
]);
const NATIVE_FORMATS = new Set(["trace-event-json", "cdp-return-as-stream"]);
const REQUIRED_CATEGORIES = new Set([
  "devtools.timeline", "disabled-by-default-devtools.timeline.frame", "disabled-by-default-devtools.timeline.layers",
  "disabled-by-default-cc.debug", "cc",
]);

function eventName(event) {
  return String(event?.name || event?.type || "").replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function timestampMs(event) {
  for (const key of ["timestamp_ms", "time_ms", "start_ms"]) {
    if (typeof event?.[key] === "number" && Number.isFinite(event[key])) return event[key];
  }
  // Chrome trace events use microseconds; fixtures use explicit ms.
  for (const key of ["ts", "timestamp"]) {
    if (typeof event?.[key] === "number" && Number.isFinite(event[key])) return event[key] / 1000;
  }
  return null;
}

function dataOf(event) {
  return event?.args?.data || event?.data || event?.args || {};
}

function frameIdOf(event) {
  const data = dataOf(event);
  const value = event?.frame_id ?? event?.frameId ?? data.frameId ?? data.frame_id
    ?? event?.args?.frameId ?? event?.args?.frame_id
    // Native compositor records use BeginFrame.args.frameSeqId.
    ?? event?.args?.frameSeqId ?? data.frameSeqId ?? data.frame_seq_id
    ?? event?.sequence_number ?? data.sequence_number;
  return value === undefined || value === null || String(value) === "" ? null : String(value);
}

function layerIdOf(event) {
  const data = dataOf(event);
  const value = event?.layer_id ?? event?.layerId ?? data.layerId ?? data.layer_id;
  return value === undefined || value === null ? null : String(value);
}

function layerTreeIdOf(event) {
  const data = dataOf(event);
  const value = event?.layer_tree_id ?? event?.layerTreeId ?? data.layerTreeId ?? data.layer_tree_id;
  return value === undefined || value === null ? null : String(value);
}

function snapshotOf(event) {
  return event?.args?.snapshot || dataOf(event).snapshot || event?.snapshot || null;
}

function layersOf(snapshotEvent) {
  return snapshotOf(snapshotEvent)?.active_tree?.layers || [];
}

function isCanvasLayer(layer, selector = "canvas") {
  if (!layer || typeof layer !== "object") return false;
  const name = String(layer.layer_name || "");
  const base = String(layer.base_type || "");
  const reasons = Array.isArray(layer.compositing_reasons) ? layer.compositing_reasons.join(" ") : "";
  const canvasLike = /htmlcanvas|canvas/i.test(name) || /canvas/i.test(reasons);
  if (!canvasLike && selector !== "canvas") return false;
  if (selector === "canvas") return canvasLike || /texturelayerimpl/i.test(base);
  const match = String(selector).match(/^#([A-Za-z_][A-Za-z0-9_-]*)$/);
  if (!match) return canvasLike;
  return name.includes(`id='${match[1]}'`) || name.includes(`id=\"${match[1]}\"`);
}

function canvasLayersAt(snapshotEvent, target = {}) {
  const selector = target.canvas_selector || target.canvasSelector || "canvas";
  const targetLayers = (target.layer_ids || target.layerIds || []).map(String);
  return layersOf(snapshotEvent).filter(layer => {
    if (targetLayers.length && !targetLayers.includes(String(layer.layer_id))) return false;
    return isCanvasLayer(layer, selector);
  });
}

function explicitAttribution(event) {
  const data = dataOf(event);
  const value = event?.attribution ?? event?.canvas_attribution ?? data.attribution
    ?? data.canvasAttribution ?? data.layerName ?? data.layer_name;
  if (typeof value !== "string") return null;
  const normalized = value.toLowerCase().replace(/[ _]/g, "-");
  if (["game-canvas", "game", "canvas", "target"].includes(normalized)) return "game-canvas";
  if (["other-layer", "other", "chrome"].includes(normalized)) return "other-layer";
  return "ambiguous";
}

function targetForEvent(event, target = {}, {allowSynthetic = false} = {}) {
  // Native caller-supplied IDs and canvas:true flags are hints only. They are
  // considered by nativeCanvasAttribution only after renderer/layer and
  // pixel-change evidence are joined. Fixture records retain explicit labels
  // so deterministic qualification boundaries remain cheap to test.
  if (allowSynthetic) {
    const explicit = explicitAttribution(event);
    if (explicit) return explicit;
    if (event?.canvas === true || dataOf(event).canvas === true) return "game-canvas";
    const layer = layerIdOf(event);
    const targetLayers = (target.layer_ids || target.layerIds || (target.layer_id ? [target.layer_id] : [])).map(String);
    if (layer && targetLayers.length) return targetLayers.includes(layer) ? "game-canvas" : "other-layer";
    const tree = layerTreeIdOf(event);
    const targetTrees = (target.layer_tree_ids || target.layerTreeIds || (target.layer_tree_id ? [target.layer_tree_id] : [])).map(String);
    if (tree && targetTrees.length) return targetTrees.includes(tree) ? "game-canvas" : "other-layer";
    return null;
  }
  const process = event?.renderer_process_id ?? dataOf(event).rendererProcessId ?? dataOf(event).renderer_process_id;
  if (target.renderer_process_id !== undefined && process !== undefined && String(process) !== String(target.renderer_process_id)) return "other-layer";
  return null;
}

function deriveRendererContext(events, target, snapshots) {
  const mainFrameIds = new Set();
  const rendererPidsByFrame = new Map();
  const rendererPids = new Set();
  const mainThreadByPid = new Map();
  for (const event of events) {
    const name = eventName(event);
    const data = dataOf(event);
    if (name === "tracingstartedinbrowser") {
      for (const frame of data.frames || []) {
        if (frame?.frame && (frame.isInPrimaryMainFrame === true || frame.isOutermostMainFrame === true || (!frame.parent && frame.url))) mainFrameIds.add(String(frame.frame));
        if (frame?.frame !== undefined && frame?.processId !== undefined) {
          const pid = String(frame.processId);
          rendererPidsByFrame.set(String(frame.frame), pid);
          rendererPids.add(pid);
        }
      }
    }
    if (name === "framecommittedinbrowser" || name === "commitload") {
      const frame = data;
      if (frame?.frame !== undefined && event.pid !== undefined) {
        const pid = String(frame.processId ?? event.pid);
        rendererPidsByFrame.set(String(frame.frame), pid);
        rendererPids.add(pid);
        if (frame.isInPrimaryMainFrame === true || frame.isOutermostMainFrame === true) mainFrameIds.add(String(frame.frame));
      }
    }
    if (name === "threadname" && String(data.name || "") === "CrRendererMain" && event.pid !== undefined) mainThreadByPid.set(String(event.pid), String(event.tid));
  }
  const requestedMain = target.main_frame_id || target.mainFrameId;
  if (requestedMain) mainFrameIds.add(String(requestedMain));
  const targetPid = target.renderer_process_id ?? target.renderer_pid;
  if (targetPid !== undefined && targetPid !== null) rendererPids.add(String(targetPid));

  // Generic traces often omit Meta's process records. A canvas layer observed
  // in LayerTreeHostImpl snapshots safely discovers the candidate renderer;
  // competing candidates remain ambiguous.
  const canvasPidCounts = new Map();
  for (const item of snapshots) {
    if (!canvasLayersAt(item.event, target).length || item.event.pid === undefined) continue;
    const pid = String(item.event.pid);
    canvasPidCounts.set(pid, (canvasPidCounts.get(pid) || 0) + 1);
  }
  if (!targetPid && canvasPidCounts.size) {
    const max = Math.max(...canvasPidCounts.values());
    for (const [pid, count] of canvasPidCounts) if (count === max) rendererPids.add(pid);
  }
  if (!rendererPids.size && snapshots.length) rendererPids.add(String(snapshots[0].event.pid));
  const mainThreads = new Set(mainThreadByPid.values());
  for (const event of events) {
    if (event.pid !== undefined && rendererPids.has(String(event.pid)) && event.tid !== undefined && eventName(event) === "beginmainthreadframe") {
      mainThreads.add(String(event.tid));
      if (!mainThreadByPid.has(String(event.pid))) mainThreadByPid.set(String(event.pid), String(event.tid));
    }
  }
  return {mainFrameIds, rendererPids, mainThreadByPid, mainThreads, rendererPidsByFrame, canvasPidCounts};
}

function isNativeCanvasUpdate(event) {
  const data = dataOf(event);
  // A generic TextureLayer push only proves compositor bookkeeping. It can
  // occur while the canvas remains visually unchanged, so it is not a
  // presentation marker. Accept only explicit target-canvas update/paint
  // markers supplied by a trace producer.
  return event.canvas_updated === true || data.canvasUpdated === true || data.canvas_updated === true
    || /canvas.*(update|paint)/i.test(String(event.name || ""));
}

function nativeUpdateIndex(events) {
  const any = [];
  const withoutPid = [];
  const byPid = new Map();
  for (const event of events) {
    if (!isNativeCanvasUpdate(event)) continue;
    const time = timestampMs(event);
    if (time === null) continue;
    const row = {time, pid: event.pid === undefined ? undefined : String(event.pid)};
    any.push(row);
    if (row.pid === undefined) withoutPid.push(row);
    else {
      if (!byPid.has(row.pid)) byPid.set(row.pid, []);
      byPid.get(row.pid).push(row);
    }
  }
  const order = (a, b) => a.time - b.time;
  any.sort(order);
  withoutPid.sort(order);
  for (const rows of byPid.values()) rows.sort(order);
  return {any, withoutPid, byPid};
}

function hasTimeWithin(rows, time, toleranceMs = 20) {
  let low = 0;
  let high = rows.length;
  const minimum = time - toleranceMs;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (rows[middle].time < minimum) low = middle + 1;
    else high = middle;
  }
  return low < rows.length && rows[low].time <= time + toleranceMs;
}

function nativeUpdateAt(events, time, target, processId, index = null) {
  if (index) {
    if (processId === undefined) return hasTimeWithin(index.any, time);
    return hasTimeWithin(index.byPid.get(String(processId)) || [], time)
      || hasTimeWithin(index.withoutPid, time);
  }
  return events.some(event => {
    const at = timestampMs(event);
    if (at === null || Math.abs(at - time) > 20) return false;
    if (processId !== undefined && event.pid !== undefined && String(event.pid) !== String(processId)) return false;
    return isNativeCanvasUpdate(event);
  });
}

function snapshotIndex(snapshots) {
  const all = snapshots.slice().sort((a, b) => a.time - b.time);
  const byPid = new Map();
  for (const snapshot of all) {
    if (snapshot.event?.pid === undefined) continue;
    const pid = String(snapshot.event.pid);
    if (!byPid.has(pid)) byPid.set(pid, []);
    byPid.get(pid).push(snapshot);
  }
  return {all, byPid};
}

function latestSnapshotGroup(rows, time) {
  let low = 0;
  let high = rows.length;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (rows[middle].time <= time) low = middle + 1;
    else high = middle;
  }
  const end = low - 1;
  if (end < 0) return [];
  const latestTime = rows[end].time;
  let start = end;
  while (start > 0 && rows[start - 1].time === latestTime) start -= 1;
  return rows.slice(start, end + 1);
}

function canvasActivityIntervals(parsed) {
  const samples = parsed.canvas_samples || parsed.metadata?.canvas_samples || [];
  const rows = Array.isArray(samples) ? samples.map(item => ({
    time: item?.timestamp_ms ?? item?.time_ms ?? item?.time,
    hash: item?.hash ?? item?.digest ?? item?.signature,
  })).filter(item => typeof item.time === "number" && Number.isFinite(item.time) && typeof item.hash === "string")
    .sort((a, b) => a.time - b.time) : [];
  const intervals = [];
  for (let index = 1; index < rows.length; index += 1) if (rows[index - 1].hash !== rows[index].hash) intervals.push([rows[index - 1].time, rows[index].time]);
  return intervals;
}

function canvasChangeTimes(parsed) {
  const samples = parsed.canvas_samples || parsed.metadata?.canvas_samples || [];
  const rows = Array.isArray(samples) ? samples.map(item => ({
    time: item?.timestamp_ms ?? item?.time_ms ?? item?.time,
    hash: item?.hash ?? item?.digest ?? item?.signature,
  })).filter(item => typeof item.time === "number" && Number.isFinite(item.time) && typeof item.hash === "string")
    .sort((a, b) => a.time - b.time) : [];
  const changes = [];
  for (let index = 1; index < rows.length; index += 1) {
    if (rows[index - 1].hash !== rows[index].hash) changes.push(rows[index].time);
  }
  return changes;
}

function hasCanvasActivity(parsed, time, target, snapshots, sourceEvent, updateIndex = null) {
  if (parsed.format === "fixture") return true;
  const process = sourceEvent?.pid;
  return nativeUpdateAt(parsed.events, time, target, process, updateIndex);
}

function markCanvasSampleEvidence(frames, parsed) {
  if (parsed.format === "fixture") return;
  const changes = canvasChangeTimes(parsed);
  if (!changes.length) return;
  // A sample is associated with at most one native frame. The tolerance is
  // half of a 60 Hz frame interval; sparse samples therefore mark sparse
  // frames instead of upgrading an entire interval to 60 Hz.
  const toleranceMs = 9;
  const used = new Set();
  for (const change of changes) {
    let bestIndex = -1;
    let bestDistance = Infinity;
    for (let index = 0; index < frames.length; index += 1) {
      const row = frames[index];
      if (used.has(index) || row.ambiguous || row.attribution !== "game-canvas" || !row.draw) continue;
      const distance = Math.abs(row.start_ms - change);
      if (distance <= toleranceMs && distance < bestDistance) {
        bestIndex = index;
        bestDistance = distance;
      }
    }
    if (bestIndex >= 0) {
      used.add(bestIndex);
      const row = frames[bestIndex];
      row.presentation_evidence = true;
      row.attribution_source = "renderer-process+layer-tree-canvas+read-only-pixel-change-at-frame";
    }
  }
}

function nativeCanvasAttribution(parsed, snapshots, time, target, sourceEvent = null) {
  if (!snapshots.length || time === null) return null;
  const candidates = snapshots.filter(snapshot => {
    if (sourceEvent?.pid !== undefined && snapshot.event?.pid !== sourceEvent.pid) return false;
    if (target.renderer_process_id !== undefined && String(snapshot.event?.pid) !== String(target.renderer_process_id)) return false;
    return snapshot.time <= time;
  });
  if (!candidates.length) return null;
  const latestTime = candidates[candidates.length - 1].time;
  const group = candidates.filter(snapshot => snapshot.time === latestTime);
  const layers = group.flatMap(snapshot => canvasLayersAt(snapshot.event, target));
  if (layers.length > 1) return "ambiguous";
  if (layers.length !== 1) return null;
  return "game-canvas";
}

function mergeRow(row, event, target, {allowSynthetic = false} = {}) {
  const name = eventName(event);
  row.events.push(name || "unknown");
  const time = timestampMs(event);
  if (time !== null) row.start_ms = row.start_ms === null ? time : Math.min(row.start_ms, time);
  const data = dataOf(event);
  if (DRAW_NAMES.has(name) || data.draw === true || event.draw === true) row.draw = true;
  if (DROP_NAMES.has(name) || data.dropped === true || event.dropped === true) row.dropped = true;
  if (PARTIAL_NAMES.has(name) || data.isPartial === true || data.partial === true || event.isPartial === true || event.partial === true) row.isPartial = true;
  if (IDLE_NAMES.has(name) || data.idle === true || event.idle === true) row.idle = true;
  const attribution = targetForEvent(event, target, {allowSynthetic});
  if (attribution === "ambiguous") row.ambiguous = true;
  else if (attribution && row.attribution && row.attribution !== attribution) row.ambiguous = true;
  else if (attribution) row.attribution = attribution;
  const layer = layerIdOf(event);
  if (layer) row.layer_id = layer;
  if (event.duration_ms !== undefined) row.duration_ms = event.duration_ms;
  if (data.duration_ms !== undefined) row.duration_ms = data.duration_ms;
}

export function parseTracePayload(payload) {
  if (Buffer.isBuffer(payload) || payload instanceof Uint8Array) payload = Buffer.from(payload).toString("utf8");
  if (typeof payload === "string") {
    const text = payload.trim();
    if (!text) throw inputError("empty CDP trace stream", "/trace");
    try {
      payload = JSON.parse(text);
    } catch (error) {
      const events = [];
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        try { events.push(JSON.parse(line)); } catch (lineError) { throw inputError(`unparsed CDP trace line: ${lineError.message}`, "/trace"); }
      }
      payload = events;
    }
  }
  if (Array.isArray(payload)) return {events: payload, metadata: {}, completion: {}, format: "trace-event-json"};
  requireObject(payload, "/trace");
  const events = payload.traceEvents || payload.events || payload.data;
  if (!Array.isArray(events)) throw inputError("trace must contain traceEvents/events array", "/trace/traceEvents");
  return {
    events,
    metadata: payload.metadata || {},
    completion: payload.completion || payload.tracingComplete || {},
    dataLossOccurred: Object.prototype.hasOwnProperty.call(payload, "dataLossOccurred") ? payload.dataLossOccurred : undefined,
    format: payload.format || "trace-event-json",
    transfer_mode: payload.transfer_mode || payload.transferMode,
    categories: payload.categories || payload.traceConfig?.includedCategories || payload.metadata?.categories || [],
    raw_bytes: payload.raw_bytes,
    raw_stream_hash: payload.raw_stream_hash,
    raw_stream_path: payload.raw_stream_path,
    canvas_samples: payload.canvas_samples || payload.metadata?.canvas_samples,
    canvas_instrumentation: payload.canvas_instrumentation || payload.metadata?.canvas_instrumentation,
    measurement: payload.measurement || payload.metadata?.measurement,
  };
}

function eventPhase(event) {
  return String(event?.ph || "").toLowerCase();
}

function shouldProcessCommit(event) {
  const phase = eventPhase(event);
  return phase !== "e" && phase !== "f";
}

function eventAllowed(event, context, target) {
  if (event?.pid !== undefined && context.rendererPids.size && !context.rendererPids.has(String(event.pid))) return false;
  const tree = layerTreeIdOf(event);
  const targetTrees = (target.layer_tree_ids || target.layerTreeIds || (target.layer_tree_id ? [target.layer_tree_id] : [])).map(String);
  if (tree && targetTrees.length && !targetTrees.includes(tree)) return false;
  return true;
}

export function buildFrameModel(payload, {target = {}, startMs = -Infinity, endMs = Infinity} = {}) {
  const parsed = parseTracePayload(payload);
  if (parsed.format && !NATIVE_FORMATS.has(parsed.format) && parsed.format !== "fixture") return {...parsed, frames: [], attributed: 0, ambiguous: false, unparsed: true, errors: [`unsupported trace format ${parsed.format}`]};
  const ordered = parsed.events.map((event, index) => ({event, index})).filter(item => item.event && typeof item.event === "object")
    .sort((a, b) => (timestampMs(a.event) ?? Infinity) - (timestampMs(b.event) ?? Infinity) || a.index - b.index);
  const snapshots = ordered.map(item => ({event: item.event, time: timestampMs(item.event)}))
    .filter(item => item.time !== null && eventName(item.event) === "layertreehostimplsnapshot");
  const snapshotLookup = snapshotIndex(snapshots);
  const updateLookup = nativeUpdateIndex(parsed.events);
  const context = deriveRendererContext(ordered.map(item => item.event), target, snapshots);
  const allowSynthetic = parsed.format === "fixture";
  const rows = [];
  const beginQueue = [];
  const beginById = new Map();
  let ordinal = 0;
  let lastFrame = null;
  let mainFrameCommitted = false;
  let mainFrameRequested = false;
  let pendingCommit = null;
  let pendingActivation = null;
  let lastBeginFrame = null;
  let lastNeedsBeginFrame = null;
  let activeLayerTree = null;

  const emit = (info, event, {draw = false, dropped = false, isPartial = false} = {}) => {
    const baseId = String(info.id);
    const id = rows.some(row => row.id === baseId) ? `${baseId}#${ordinal++}` : baseId;
    const row = {
      id, start_ms: info.start_ms, duration_ms: null, draw, dropped: Boolean(dropped), isPartial: Boolean(isPartial), idle: false,
      attribution: null, attribution_source: null, presentation_evidence: false, layer_id: null, ambiguous: false, events: [],
    };
    if (event) mergeRow(row, event, target, {allowSynthetic});
    if (draw) row.draw = true;
    if (dropped) row.dropped = true;
    if (isPartial) row.isPartial = true;
    if (!allowSynthetic) {
      const sourcePid = event?.pid;
      const targetPid = target.renderer_process_id;
      const snapshotRows = sourcePid !== undefined
        ? snapshotLookup.byPid.get(String(sourcePid)) || []
        : targetPid !== undefined
          ? snapshotLookup.byPid.get(String(targetPid)) || []
          : snapshotLookup.all;
      const candidates = (sourcePid !== undefined && targetPid !== undefined && String(sourcePid) !== String(targetPid))
        ? [] : latestSnapshotGroup(snapshotRows, row.start_ms);
      const nativeAttribution = nativeCanvasAttribution(parsed, candidates, row.start_ms, target, event);
      if (nativeAttribution === "ambiguous") row.ambiguous = true;
      else if (nativeAttribution === "game-canvas") {
        row.attribution = "game-canvas";
        row.presentation_evidence = hasCanvasActivity(parsed, row.start_ms, target, snapshots, event, updateLookup);
        row.attribution_source = row.presentation_evidence
          ? "renderer-process+layer-tree-canvas+read-only-pixel-change"
          : "renderer-process+layer-tree-canvas-without-presentation-proof";
      }
    }
    rows.push(row);
    return row;
  };
  const startFrame = (time, id) => {
    if (lastFrame) lastFrame.idle = true;
    lastFrame = {start_ms: time, id: String(id)};
  };
  const processPendingOnDraw = seqId => {
    if (!beginById.has(seqId)) return [];
    const visible = [];
    while (beginQueue.length && beginQueue[0] !== seqId) {
      const id = beginQueue.shift();
      const info = beginById.get(id);
      beginById.delete(id);
      if (info?.dropped) visible.push(info);
    }
    const current = beginById.get(seqId);
    if (current) visible.push(current);
    beginById.delete(seqId);
    const index = beginQueue.indexOf(seqId);
    if (index >= 0) beginQueue.splice(index, 1);
    return visible;
  };

  for (const {event} of ordered) {
    if (allowSynthetic) {
      const name = eventName(event);
      const direct = name === "frame" || event.frame === true || event.kind === "frame";
      if (direct) {
        const time = timestampMs(event);
        emit({id: frameIdOf(event) || event.id || `fixture-${ordinal++}`, start_ms: time}, event, {
          draw: Boolean(event.draw || dataOf(event).draw), dropped: Boolean(event.dropped || dataOf(event).dropped),
          isPartial: Boolean(event.isPartial || event.partial || dataOf(event).isPartial || dataOf(event).partial),
        });
      }
      continue;
    }
    const name = eventName(event);
    if (!COMPOSITOR_NAMES.has(name) && !MAIN_MARKERS.has(name)) continue;
    if (!eventAllowed(event, context, target)) continue;
    const time = timestampMs(event);
    const tree = layerTreeIdOf(event);
    if (name === "setlayertreeid") {
      const data = dataOf(event);
      const frame = data.frame || data.frameId;
      const main = target.main_frame_id || target.mainFrameId;
      if (!main || !frame || String(frame) === String(main) || context.mainFrameIds.has(String(frame))) activeLayerTree = data.layerTreeId ?? data.layer_tree_id ?? null;
      continue;
    }
    if (tree && activeLayerTree !== null && String(activeLayerTree) !== tree) continue;
    if (name === "beginframe") {
      const id = frameIdOf(event);
      if (id !== null && !beginById.has(id)) {
        beginById.set(id, {id, start_ms: time, dropped: false, isPartial: false, event});
        beginQueue.push(id);
      }
      lastBeginFrame = time;
      continue;
    }
    if (name === "droppedframe") {
      const id = frameIdOf(event);
      if (id !== null) {
        let info = beginById.get(id);
        if (!info) {
          info = {id, start_ms: time, dropped: true, isPartial: Boolean(dataOf(event).hasPartialUpdate || event.hasPartialUpdate), event};
          beginById.set(id, info);
          beginQueue.push(id);
        }
        info.dropped = true;
        info.isPartial = info.isPartial || Boolean(dataOf(event).hasPartialUpdate || event.hasPartialUpdate);
      }
      continue;
    }
    if (name === "requestmainthreadframe") {
      if (lastFrame) mainFrameRequested = true;
      continue;
    }
    if (MAIN_MARKERS.has(name)) {
      const mainTid = context.mainThreadByPid.get(String(event.pid));
      if (mainTid && event.tid !== undefined && String(event.tid) !== String(mainTid)) continue;
      if (!pendingCommit) pendingCommit = {triggerTime: time, paints: [], mainFrameId: null};
      if (name === "beginmainthreadframe") {
        const data = dataOf(event);
        pendingCommit.mainFrameId = data.frameId ?? data.frame_id ?? null;
      }
      continue;
    }
    if (name === "commit" || name === "compositelayers") {
      if (shouldProcessCommit(event) && pendingCommit) {
        pendingActivation = pendingCommit;
        pendingCommit = null;
        mainFrameRequested = false;
        mainFrameCommitted = true;
      }
      continue;
    }
    if (name === "activatelayertree") {
      if (pendingActivation && lastNeedsBeginFrame === null) pendingActivation = null;
      continue;
    }
    if (name === "needsbeginframechanged") {
      const data = dataOf(event);
      const needs = data.needsBeginFrame ?? data.needs_begin_frame;
      if (needs === true || needs === 1) lastNeedsBeginFrame = time;
      continue;
    }
    if (name === "drawframe") {
      if (!lastFrame) startFrame(time, frameIdOf(event) || `frame-${ordinal++}`);
      if (!(mainFrameCommitted || !mainFrameRequested)) continue;
      if (lastNeedsBeginFrame !== null) {
        const idleEnd = pendingActivation?.triggerTime ?? lastBeginFrame ?? lastNeedsBeginFrame;
        if (idleEnd > lastFrame.start_ms) lastFrame.idle = true;
        lastNeedsBeginFrame = null;
      }
      const id = frameIdOf(event);
      if (id === null) continue;
      const visible = processPendingOnDraw(id);
      for (const info of visible) {
        emit({id: info.id, start_ms: info.start_ms}, info.event, {draw: false, dropped: info.dropped, isPartial: info.isPartial});
      }
      const current = visible.find(info => String(info.id) === String(id));
      if (current) {
        const row = rows[rows.length - 1];
        mergeRow(row, event, target);
        row.draw = true;
        lastFrame = row;
      } else if (visible.length) {
        lastFrame = rows[rows.length - 1];
      }
      mainFrameCommitted = false;
      continue;
    }
    if (IDLE_NAMES.has(name)) {
      const id = frameIdOf(event);
      if (id !== null && beginById.has(id)) beginById.get(id).idle = true;
    }
  }

  const frames = rows.filter(row => row.start_ms !== null && row.start_ms >= startMs && row.start_ms < endMs)
    .sort((a, b) => a.start_ms - b.start_ms || a.id.localeCompare(b.id));
  markCanvasSampleEvidence(frames, parsed);
  const ambiguous = frames.some(row => row.ambiguous);
  return {
    ...parsed, frames, ambiguous, attributed: frames.filter(row => row.attribution === "game-canvas").length, unparsed: false,
    errors: ambiguous ? ["ambiguous frame or canvas attribution"] : [],
    renderer: {process_ids: [...context.rendererPids], main_frame_ids: [...context.mainFrameIds], main_thread_ids: [...context.mainThreads]},
  };
}

export function frameRows(payload, options = {}) { return buildFrameModel(payload, options).frames; }

export function callbackTimes(callbacks) {
  if (!Array.isArray(callbacks)) return [];
  return callbacks.map(item => typeof item === "number" ? item : item?.timestamp_ms ?? item?.time_ms ?? item?.ts)
    .filter(value => typeof value === "number" && Number.isFinite(value)).sort((a, b) => a - b);
}

function ratio(count, denominator) { return denominator > 0 ? count / denominator : 0; }
function failure(code, pointer, expected, observed) { return {code, pointer, expected, observed}; }

function validSamplingCoverage(value) {
  const region = value?.resolved_region;
  const buffer = value?.drawing_buffer;
  const viewport = value?.viewport;
  return value?.explicit === true
    && ["drawing-buffer", "viewport"].includes(value?.coordinate_space)
    && region && Number.isInteger(region.x) && Number.isInteger(region.y)
    && Number.isInteger(region.width) && Number.isInteger(region.height)
    && region.x >= 0 && region.y >= 0 && region.width > 0 && region.height > 0
    && buffer && Number.isInteger(buffer.width) && Number.isInteger(buffer.height)
    && buffer.width > 0 && buffer.height > 0
    && region.x + region.width <= buffer.width && region.y + region.height <= buffer.height
    && viewport && Number.isFinite(viewport.width) && viewport.width > 0
    && Number.isFinite(viewport.height) && viewport.height > 0
    && Number.isFinite(value.dpr) && value.dpr > 0
    && Number.isInteger(value.sample_pixels) && value.sample_pixels === region.width * region.height;
}

function validAsyncReadback(value) {
  return value?.method === "webgl2.pixel-pack-buffer+fence-sync"
    && value?.asynchronous === true
    && Array.isArray(value.api)
    && value.api.includes("PIXEL_PACK_BUFFER")
    && value.api.includes("readPixels-offset")
    && value.api.includes("fenceSync")
    && value.api.includes("clientWaitSync-timeout-0")
    && value.api.includes("getBufferSubData")
    && Number.isInteger(value.max_pending) && value.max_pending >= 1 && value.max_pending <= 8
    && Number.isInteger(value.allocated_buffers) && value.allocated_buffers >= 0
    && Number.isInteger(value.queued) && value.queued >= 0
    && Number.isInteger(value.completed) && value.completed >= 0
    && Number.isInteger(value.lost) && value.lost >= 0
    && Number.isInteger(value.errors) && value.errors >= 0
    && Number.isInteger(value.context_losses) && value.context_losses >= 0
    && Number.isInteger(value.poll_count) && value.poll_count >= 0
    && Number.isInteger(value.pending_at_cleanup) && value.pending_at_cleanup >= 0
    && value.cleanup_observed === true
    && ["queue_duration_ms", "wait_duration_ms", "copy_duration_ms", "poll_duration_ms"]
      .every(key => typeof value[key] === "number" && Number.isFinite(value[key]) && value[key] >= 0);
}

function nativeTraceFailures(parsed, startMs, endMs) {
  const failures = [];
  if (!NATIVE_FORMATS.has(parsed.format)) failures.push(failure("unparsed-format", "/trace/format", [...NATIVE_FORMATS], parsed.format));
  const completion = parsed.completion || {};
  if (parsed.format === "cdp-return-as-stream") {
    if (completion.dataLossOccurred !== false || typeof completion.stream !== "string" || completion.stream.length === 0
      || (parsed.transfer_mode && parsed.transfer_mode !== "ReturnAsStream") || (completion.transferMode && completion.transferMode !== "ReturnAsStream")) {
      failures.push(failure("missing-completion-metadata", "/trace/completion", "stream, transferMode ReturnAsStream, dataLossOccurred:false", completion));
    }
    const categories = new Set(parsed.categories || []);
    const missing = [...REQUIRED_CATEGORIES].filter(category => !categories.has(category));
    if (missing.length) failures.push(failure("trace-categories", "/trace/categories", [...REQUIRED_CATEGORIES], missing));
    if (!Number.isInteger(parsed.raw_bytes) || parsed.raw_bytes <= 0 || !/^sha256:[0-9a-f]{64}$/i.test(parsed.raw_stream_hash || "")) {
      failures.push(failure("missing-raw-stream", "/trace/raw_stream_hash", "raw bytes and sha256 identity", {raw_bytes: parsed.raw_bytes, raw_stream_hash: parsed.raw_stream_hash}));
    }
  }
  if (parsed.metadata?.clock_reconciled !== true) failures.push(failure("clock-mismatch", "/trace/metadata/clock_reconciled", true, parsed.metadata?.clock_reconciled));
  if (typeof parsed.metadata?.window_start_ms !== "number" || parsed.metadata.window_start_ms > startMs
    || typeof parsed.metadata?.window_end_ms !== "number" || parsed.metadata.window_end_ms < endMs) {
    failures.push(failure("unpadded-window", "/trace/metadata", `window covers [${startMs}, ${endMs})`, parsed.metadata));
  }
  const instrumentation = parsed.canvas_instrumentation || {};
  if (instrumentation.presentation !== "render-callback-post-callback" || instrumentation.read_only !== true
      || instrumentation.preserve_drawing_buffer !== false) {
    failures.push(failure("missing-native-presentation-observation", "/trace/canvas_instrumentation", "read-only render-callback observation with preserveDrawingBuffer:false", instrumentation));
  }
  const readback = instrumentation.readback || parsed.measurement?.instrumented?.readback;
  if (!validAsyncReadback(readback)) {
    failures.push(failure("missing-asynchronous-readback", "/trace/canvas_instrumentation/readback", "bounded WebGL2 PBO/fence readback with zero-timeout polling and observed cleanup", readback || null));
  }
  const samples = Array.isArray(parsed.canvas_samples) ? parsed.canvas_samples : [];
  if (!samples.some(item => item?.source === "render-callback-post-callback")) {
    failures.push(failure("missing-render-callback-samples", "/trace/canvas_samples", "at least one post-callback sample", samples.length));
  }
  const sampling = instrumentation.sampling || instrumentation.sample_coverage || parsed.measurement?.sampling;
  if (!validSamplingCoverage(sampling)) {
    failures.push(failure("missing-sampling-coverage", "/trace/canvas_instrumentation/sampling", "explicit contained drawing-buffer coverage with viewport and DPR", sampling || null));
  }
  const sampledRows = samples.filter(item => item?.source === "render-callback-post-callback");
  if (sampledRows.some(item => typeof item.duration_ms !== "number" || !Number.isFinite(item.duration_ms) || item.duration_ms < 0)) {
    failures.push(failure("missing-sample-duration", "/trace/canvas_samples", "every post-callback sample records a non-negative duration_ms", sampledRows));
  }
  if (sampledRows.some(item => !Number.isInteger(item.callback_index) || item.callback_index < 0
      || typeof item.origin_timestamp_ms !== "number" || !Number.isFinite(item.origin_timestamp_ms)
      || !["complete", "lost", "error"].includes(item.completion_status))) {
    failures.push(failure("invalid-readback-association", "/trace/canvas_samples", "each sample retains callback origin and completion/loss status", sampledRows));
  }
  const perturbation = instrumentation.measurement_perturbation || parsed.measurement?.perturbation;
  if (!perturbation || perturbation.status !== "observed" || perturbation.basis !== "control-vs-instrumented"
      || !Number.isFinite(perturbation.callback_rate_delta_hz)
      || !Number.isInteger(perturbation.control_callbacks) || !Number.isInteger(perturbation.instrumented_callbacks)
      || !Number.isFinite(perturbation.control_callback_rate_hz) || !Number.isFinite(perturbation.instrumented_callback_rate_hz)) {
    failures.push(failure("missing-measurement-perturbation", "/trace/canvas_instrumentation/measurement_perturbation", "observed control-vs-instrumented comparison", perturbation || null));
  }
  const warmup = parsed.measurement?.warmup;
  if (!warmup || warmup.status !== "observed" || !Number.isFinite(warmup.observed_ms) || warmup.observed_ms <= 0) {
    failures.push(failure("missing-observed-warmup", "/trace/measurement/warmup", "observed warm-up interval", warmup || null));
  }
  for (const [name, phase] of [["control", parsed.measurement?.control], ["instrumented", parsed.measurement?.instrumented]]) {
    if (!phase || phase.status !== "observed" || !Number.isFinite(phase.observed_ms) || phase.observed_ms <= 0
        || !Number.isInteger(phase.callbacks) || !Number.isFinite(phase.callback_rate_hz)) {
      failures.push(failure(`missing-observed-${name}`, `/trace/measurement/${name}`, "observed callback phase", phase || null));
    }
  }
  const control = parsed.measurement?.control;
  const instrumented = parsed.measurement?.instrumented;
  if (control && instrumented && control.requested_ms !== instrumented.requested_ms) {
    failures.push(failure("incomparable-control-duration", "/trace/measurement/control/requested_ms", instrumented.requested_ms, control.requested_ms));
  }
  const lifecycle = parsed.measurement?.lifecycle;
  if (!lifecycle || lifecycle.status === "fixture" || lifecycle.reset?.observed !== true
      || lifecycle.reset?.method !== "page.reload"
      || !Array.isArray(lifecycle.phase_transitions) || lifecycle.phase_transitions.length < 2
      || lifecycle.phase_transitions.some(item => item?.start_observed !== true)) {
    failures.push(failure("missing-observed-reset-lifecycle", "/trace/measurement/lifecycle", "observed page reset and control/instrumented phase starts", lifecycle || null));
  }
  return failures;
}

export function qualifyPerformance({cell, trace, callbacks = []}) {
  requireObject(cell, "/cell");
  const window = cell.window || {};
  const startMs = window.start_ms ?? cell.start_ms;
  const endMs = window.end_ms ?? cell.end_ms;
  if (typeof startMs !== "number" || typeof endMs !== "number" || !(endMs > startMs)) return {status: "unverified", failures: [failure("missing-window", "/cell/window", "finite start_ms < end_ms", window)], metrics: {fps_claim: false}};
  const T = (endMs - startMs) / 1000;
  const parsed = parseTracePayload(trace);
  const failures = parsed.format === "fixture" ? [] : nativeTraceFailures(parsed, startMs, endMs);
  if (parsed.dataLossOccurred === true || parsed.completion?.dataLossOccurred === true) {
    failures.push(failure("trace-data-loss", "/trace/completion/dataLossOccurred", false, true));
  }
  const model = buildFrameModel(parsed, {target: cell.game_canvas || cell.target || {}, startMs, endMs});
  if (model.unparsed) failures.push(failure("unparsed-format", "/trace/format", [...NATIVE_FORMATS], parsed.format));
  if (model.ambiguous) failures.push(failure("ambiguous-attribution", "/trace/frames", "one game-canvas attribution", model.errors));
  const frames = model.frames;
  const targetFrames = frames.filter(row => row.attribution === "game-canvas" && (row.presentation_evidence !== false || parsed.format === "fixture"));
  if (targetFrames.length === 0) failures.push(failure("missing-canvas-attribution", "/trace/frames", "at least one observed game-canvas frame", 0));
  const callback = callbackTimes(callbacks).filter(time => time >= startMs && time < endMs);
  const intervals = callback.slice(1).map((time, index) => time - callback[index]);
  const intervalRatio = intervals.length ? intervals.filter(value => value <= 18.33).length / intervals.length : 0;
  const uniqueFlags = frames.filter(row => row.dropped || row.isPartial).length;
  const clean = targetFrames.filter(row => !row.idle && !row.dropped && !row.isPartial && row.draw);
  // Stall detection uses the native canvas-attributed frame cadence, while
  // presentation qualification separately requires evidence on each clean
  // frame. Sparse read-only samples must not manufacture a stall merely
  // because they leave most otherwise observed frames uncertified.
  const observedTargetFrames = frames.filter(row => row.attribution === "game-canvas" && !row.ambiguous);
  const targetGaps = observedTargetFrames.slice(1).map((row, index) => row.start_ms - observedTargetFrames[index].start_ms);
  const callbackGaps = callback.slice(1).map((time, index) => time - callback[index]);
  const unexplainedStall = [...targetGaps, ...callbackGaps].some(value => value > 100);
  const metrics = {
    window_start_ms: startMs, window_end_ms: endMs, duration_seconds: T, N: frames.length, C: clean.length,
    I: frames.filter(row => row.idle).length, D: uniqueFlags, callbacks: callback.length, callback_rate_hz: callback.length / T,
    callback_interval_compliance: intervalRatio, max_callback_interval_ms: intervals.length ? Math.max(...intervals) : null,
    unexplained_stall: unexplainedStall, attribution: targetFrames.length ? "game-canvas" : "unverified", fps_claim: false,
  };
  const mode = cell.mode || cell.surface || "animation";
  if (mode === "static" || mode === "static-idle") {
    const status = failures.length ? "unverified" : "qualified";
    return {status, verdict: status === "qualified" ? "qualified" : "performance: unverified", mode: "static", metrics, failures};
  }
  if (metrics.N <= 0) failures.push(failure("no-frames", "/metrics/N", "> 0", metrics.N));
  if (ratio(metrics.C, T) < 59) failures.push(failure("canvas-frame-floor", "/metrics/C", "C/T >= 59", `${metrics.C}/${T}`));
  if (ratio(metrics.D, metrics.N) > 0.01) failures.push(failure("dropped-partial-floor", "/metrics/D", "D/N <= 0.01", `${metrics.D}/${metrics.N}`));
  if (metrics.callback_rate_hz < 59) failures.push(failure("callback-rate-floor", "/metrics/callback_rate_hz", ">= 59", metrics.callback_rate_hz));
  if (intervalRatio < 0.99) failures.push(failure("callback-interval-floor", "/metrics/callback_interval_compliance", ">= 0.99", intervalRatio));
  if (unexplainedStall) failures.push(failure("unexplained-stall", "/metrics/unexplained_stall", false, true));
  const status = failures.length ? "unverified" : "qualified";
  metrics.fps_claim = status === "qualified";
  return {status, verdict: status === "qualified" ? "qualified" : "performance: unverified", mode: "animation", metrics, failures};
}

function withDeadline(promise, timeoutMs, pointer) {
  const duration = Number(timeoutMs);
  if (!Number.isFinite(duration) || duration <= 0) return Promise.reject(inputError("timeout must be a positive finite number", pointer));
  let timer;
  return Promise.race([
    Promise.resolve(promise),
    new Promise((_, reject) => { timer = setTimeout(() => reject(Object.assign(new Error("operation deadline exceeded"), {code: "timeout-process-loss", pointer})), duration); }),
  ]).finally(() => clearTimeout(timer));
}

export async function readReturnAsStream(client, handle, {timeoutMs = 30000, maxBytes = 512 * 1024 * 1024} = {}) {
  requireString(handle, "/stream_handle");
  const deadline = Date.now() + timeoutMs;
  const chunks = [];
  let bytes = 0;
  let eof = false;
  while (!eof) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) throw Object.assign(new Error("ReturnAsStream IO.read deadline exceeded"), {code: "timeout-process-loss", pointer: "/trace/raw_stream"});
    const reply = await withDeadline(client.send("IO.read", {handle}), remaining, "/trace/raw_stream");
    if (reply?.data) {
      const chunk = reply.base64Encoded ? Buffer.from(reply.data, "base64") : Buffer.from(reply.data);
      bytes += chunk.length;
      if (bytes > maxBytes) throw inputError(`trace stream exceeds ${maxBytes} bytes`, "/trace/raw_stream");
      chunks.push(chunk);
    }
    eof = reply?.eof === true;
  }
  try { await withDeadline(client.send("IO.close", {handle}), Math.max(1, deadline - Date.now()), "/trace/raw_stream"); } catch { /* preserve completion and bytes */ }
  return Buffer.concat(chunks);
}

function waitForEvent(client, eventNameValue, timeoutMs) {
  return new Promise((resolve, reject) => {
    let timer;
    const onEvent = value => { clearTimeout(timer); client.off?.(eventNameValue, onEvent); resolve(value); };
    timer = setTimeout(() => { client.off?.(eventNameValue, onEvent); reject(Object.assign(new Error(`${eventNameValue} deadline exceeded`), {code: "timeout-process-loss", pointer: "/trace/completion"})); }, timeoutMs);
    if (client.once) client.once(eventNameValue, onEvent);
    else if (client.on) client.on(eventNameValue, onEvent);
    else reject(inputError("CDP client cannot subscribe to tracingComplete", "/trace/completion"));
  });
}

export async function collectCDPTrace(client, {
  durationMs = 1000,
  categories = ["devtools.timeline", "disabled-by-default-devtools.timeline.frame", "disabled-by-default-devtools.timeline.layers", "disabled-by-default-cc.debug", "cc"],
  timeoutMs = Math.max(120000, Number(durationMs) + 60000),
} = {}) {
  if (!Number.isFinite(durationMs) || durationMs <= 0) throw inputError("durationMs must be positive and finite", "/durationMs");
  const started = Date.now();
  const deadline = Date.now() + timeoutMs;
  const completionPromise = waitForEvent(client, "Tracing.tracingComplete", Math.max(1, timeoutMs));
  await withDeadline(client.send("Tracing.start", {transferMode: "ReturnAsStream", traceConfig: {includedCategories: categories}}), Math.max(1, deadline - Date.now()), "/trace/start");
  await withDeadline(new Promise(resolve => setTimeout(resolve, durationMs)), Math.max(1, deadline - Date.now()), "/trace/window");
  await withDeadline(client.send("Tracing.end"), Math.max(1, deadline - Date.now()), "/trace/end");
  const completion = await withDeadline(completionPromise, Math.max(1, deadline - Date.now()), "/trace/completion");
  if (!completion?.stream) throw inputError("CDP tracingComplete lacked ReturnAsStream handle", "/trace/completion/stream");
  const bytes = await readReturnAsStream(client, completion.stream, {timeoutMs: Math.max(1, deadline - Date.now())});
  const trace = {
    format: "cdp-return-as-stream", traceEvents: parseTracePayload(bytes).events, completion, raw_bytes: bytes.length,
    raw_stream_hash: sha256(bytes), transfer_mode: "ReturnAsStream", categories: [...categories], capture_duration_ms: Date.now() - started,
  };
  // Keep exact bytes available to the collector without serializing a large
  // Buffer into trace.json. The collector writes this hidden value verbatim.
  Object.defineProperty(trace, "rawStream", {value: bytes, enumerable: false});
  return trace;
}

export {canvasLayersAt, canvasActivityIntervals, timestampMs};
