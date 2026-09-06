/**
 * A small, pinned-compatible projection of DevTools' FramesHandler model.
 * It joins compositor lifecycle events into unique frame rows. It deliberately
 * refuses to infer a game-canvas row from callback cadence alone.
 */
import { inputError, requireObject, requireString, sha256 } from "./_common.mjs";

const DRAW_NAMES = new Set(["drawframe", "draw_frame", "compositelayers", "compositelayerslegacy"]);
const DROP_NAMES = new Set(["droppedframe", "dropped_frame"]);
const PARTIAL_NAMES = new Set(["partialframe", "partial_frame"]);
const IDLE_NAMES = new Set(["idleframe", "idle_frame"]);
const BEGIN_NAMES = new Set(["beginframe", "begin_frame"]);

function eventName(event) {
  return String(event?.name || event?.type || "").replace(/[^a-z0-9]/gi, "").toLowerCase();
}

function timestampMs(event) {
  if (typeof event?.timestamp_ms === "number" && Number.isFinite(event.timestamp_ms)) return event.timestamp_ms;
  if (typeof event?.time_ms === "number" && Number.isFinite(event.time_ms)) return event.time_ms;
  if (typeof event?.start_ms === "number" && Number.isFinite(event.start_ms)) return event.start_ms;
  // Chrome trace events use microseconds in `ts`; fixture events use explicit
  // `*_ms` fields. Do not guess units from magnitude.
  if (typeof event?.ts === "number" && Number.isFinite(event.ts)) return event.ts / 1000;
  if (typeof event?.timestamp === "number" && Number.isFinite(event.timestamp)) return event.timestamp / 1000;
  return null;
}

function dataOf(event) {
  return event?.args?.data || event?.data || event?.args || {};
}

function frameIdOf(event) {
  const data = dataOf(event);
  const value = event?.frame_id ?? event?.frameId ?? data.frameId ?? data.frame_id
    ?? event?.args?.frameId ?? event?.args?.frame_id
    // Chrome's compositor trace uses BeginFrame.args.frameSeqId rather than
    // the fixture-friendly frameId spelling. Preserve that identity so a
    // real trace is modeled instead of silently producing N=0.
    ?? event?.args?.frameSeqId ?? data.frameSeqId ?? data.frame_seq_id
    ?? event?.sequence_number ?? data.sequence_number;
  if (value !== undefined && value !== null && String(value) !== "") return String(value);
  return null;
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

function canvasLayersAt(snapshot, target) {
  const selector = target.canvas_selector || target.canvasSelector;
  if (typeof selector !== "string" || !selector) return [];
  const layers = snapshot?.args?.snapshot?.active_tree?.layers;
  if (!Array.isArray(layers)) return [];
  const idMatch = selector.match(/^#([A-Za-z_][A-Za-z0-9_-]*)$/);
  return layers.filter(layer => {
    const name = String(layer.layer_name || "");
    if (!/HTMLCanvas|canvas/i.test(name)) return false;
    if (idMatch) return name.includes(`id='${idMatch[1]}'`) || name.includes(`id=\"${idMatch[1]}\"`);
    return selector === "canvas";
  });
}

function nativeCanvasAttribution(snapshots, time, target, sourceEvent = null) {
  if (!snapshots.length || time === null) return null;
  const processSnapshots = sourceEvent?.pid === undefined ? snapshots : snapshots.filter(snapshot => snapshot.event?.pid === sourceEvent.pid);
  if (!processSnapshots.length) return null;
  let latestTime = null;
  for (const snapshot of processSnapshots) {
    if (snapshot.time <= time) latestTime = snapshot.time;
    else break;
  }
  if (latestTime === null) return null;
  // Chrome may emit several same-timestamp snapshots for one compositor
  // update. Their active trees can be split across events, so inspect the
  // complete timestamp group before deciding that the canvas is absent.
  const layers = processSnapshots.filter(snapshot => snapshot.time === latestTime)
    .flatMap(snapshot => canvasLayersAt(snapshot.event, target));
  if (layers.length === 1) return "game-canvas";
  if (layers.length > 1) return "ambiguous";
  return null;
}

function explicitAttribution(event) {
  const data = dataOf(event);
  const value = event?.attribution ?? event?.canvas_attribution ?? data.attribution
    ?? data.canvasAttribution ?? data.layerName ?? data.layer_name;
  if (typeof value !== "string") return null;
  const normalized = value.toLowerCase().replace(/[ _]/g, "-");
  if (["game-canvas", "game", "canvas", "target"].includes(normalized)) return "game-canvas";
  if (["other-layer", "other", "chrome", "unknown"].includes(normalized)) return "other-layer";
  return "ambiguous";
}

function targetForEvent(event, target = {}) {
  const explicit = explicitAttribution(event);
  if (explicit) return explicit;
  const layer = layerIdOf(event);
  const targetLayers = target.layer_ids || target.layerIds || (target.layer_id ? [target.layer_id] : []);
  const layerMatches = targetLayers.map(String).filter(Boolean);
  if (layer && layerMatches.length === 1) return layerMatches.includes(layer) ? "game-canvas" : "other-layer";
  if (layer && layerMatches.length > 1) {
    return layerMatches.includes(layer) ? "ambiguous" : "other-layer";
  }
  const tree = layerTreeIdOf(event);
  const targetTrees = target.layer_tree_ids || target.layerTreeIds || (target.layer_tree_id ? [target.layer_tree_id] : []);
  const treeMatches = targetTrees.map(String).filter(Boolean);
  if (tree && treeMatches.length === 1) return treeMatches.includes(tree) ? "game-canvas" : "other-layer";
  if (tree && treeMatches.length > 1) return treeMatches.includes(tree) ? "ambiguous" : "other-layer";
  const process = event?.renderer_process_id ?? dataOf(event).rendererProcessId ?? dataOf(event).renderer_process_id;
  if (target.renderer_process_id && process !== undefined && String(process) !== String(target.renderer_process_id)) return "other-layer";
  if (event?.canvas === true || dataOf(event).canvas === true) return "game-canvas";
  return null;
}

function mergeRow(row, event, target) {
  const name = eventName(event);
  row.events.push(name || "unknown");
  const time = timestampMs(event);
  if (time !== null) row.start_ms = row.start_ms === null ? time : Math.min(row.start_ms, time);
  const data = dataOf(event);
  if (DRAW_NAMES.has(name) || data.draw === true || event.draw === true) row.draw = true;
  if (DROP_NAMES.has(name) || data.dropped === true || event.dropped === true) row.dropped = true;
  if (PARTIAL_NAMES.has(name) || data.isPartial === true || data.partial === true || event.isPartial === true || event.partial === true) row.isPartial = true;
  if (IDLE_NAMES.has(name) || data.idle === true || event.idle === true) row.idle = true;
  const attribution = targetForEvent(event, target);
  if (attribution === "ambiguous") row.ambiguous = true;
  else if (attribution && row.attribution && row.attribution !== attribution) row.ambiguous = true;
  else if (attribution) row.attribution = attribution;
  if (layerIdOf(event)) row.layer_id = layerIdOf(event);
  if (event.duration_ms !== undefined) row.duration_ms = event.duration_ms;
  if (data.duration_ms !== undefined) row.duration_ms = data.duration_ms;
}

export function parseTracePayload(payload) {
  if (Buffer.isBuffer(payload)) payload = payload.toString("utf8");
  if (typeof payload === "string") {
    const text = payload.trim();
    if (!text) throw inputError("empty CDP trace stream", "/trace");
    try {
      payload = JSON.parse(text);
    } catch (error) {
      const events = [];
      for (const line of text.split(/\r?\n/)) {
        if (!line.trim()) continue;
        try { events.push(JSON.parse(line)); } catch (lineError) {
          throw inputError(`unparsed CDP trace line: ${lineError.message}`, "/trace");
        }
      }
      payload = events;
    }
  }
  if (Array.isArray(payload)) return { events: payload, metadata: {}, completion: {} };
  requireObject(payload, "/trace");
  const events = payload.traceEvents || payload.events || payload.data;
  if (!Array.isArray(events)) throw inputError("trace must contain traceEvents/events array", "/trace/traceEvents");
  return {
    events,
    metadata: payload.metadata || {},
    completion: payload.completion || payload.tracingComplete || {},
    dataLossOccurred: payload.dataLossOccurred === true,
    format: payload.format || "trace-event-json",
  };
}

export function buildFrameModel(payload, { target = {}, startMs = -Infinity, endMs = Infinity } = {}) {
  const parsed = parseTracePayload(payload);
  if (parsed.format && !["trace-event-json", "cdp-return-as-stream", "fixture"].includes(parsed.format)) {
    return { ...parsed, frames: [], unparsed: true, errors: [`unsupported trace format ${parsed.format}`] };
  }
  const rows = new Map();
  const beginQueue = [];
  const beginById = new Map();
  let ordinal = 0;
  let activeLayerTree = null;
  const ordered = parsed.events.map((event, index) => ({ event, index })).sort((a, b) => {
    const at = timestampMs(a.event); const bt = timestampMs(b.event);
    return (at ?? Infinity) - (bt ?? Infinity) || a.index - b.index;
  });
  const nativeSnapshots = ordered
    .map(item => ({ event: item.event, time: timestampMs(item.event) }))
    .filter(item => item.time !== null && eventName(item.event) === "layertreehostimplsnapshot");
  const compositorNames = new Set([...BEGIN_NAMES, ...DRAW_NAMES, ...DROP_NAMES, ...PARTIAL_NAMES, ...IDLE_NAMES, "requestmainthreadframe", "activatelayertree", "needsbeginframechanged", "setlayertreeid"]);
  const emit = (info, event, flags = {}) => {
    const id = String(info.id);
    if (rows.has(id)) return;
    const row = {
      id,
      start_ms: info.start_ms,
      duration_ms: null,
      draw: false,
      dropped: Boolean(info.dropped),
      isPartial: Boolean(info.isPartial),
      idle: Boolean(info.idle),
      attribution: null,
      layer_id: null,
      ambiguous: false,
      events: [],
      ...flags,
    };
    if (event) mergeRow(row, event, target);
    const nativeAttribution = nativeCanvasAttribution(nativeSnapshots, row.start_ms, target, event);
    if (nativeAttribution === "ambiguous") row.ambiguous = true;
    else if (nativeAttribution && row.attribution && row.attribution !== nativeAttribution) row.ambiguous = true;
    else if (nativeAttribution) row.attribution = nativeAttribution;
    rows.set(id, row);
  };
  for (const { event } of ordered) {
    if (!event || typeof event !== "object") continue;
    const time = timestampMs(event);
    const name = eventName(event);
    const direct = name === "frame" || event.frame === true || event.kind === "frame";
    if (direct) {
      const id = frameIdOf(event) || event.id || `fixture-${ordinal++}`;
      emit({ id, start_ms: time, dropped: false, isPartial: false, idle: false }, event);
      continue;
    }
    if (!compositorNames.has(name)) continue;
    const tree = layerTreeIdOf(event);
    if (name === "setlayertreeid") {
      const data = dataOf(event);
      const mainFrameId = target.main_frame_id || target.mainFrameId;
      if (!mainFrameId || String(data.frame || data.frameId || "") === String(mainFrameId)) activeLayerTree = data.layerTreeId ?? data.layer_tree_id ?? null;
      continue;
    }
    const targetTrees = target.layer_tree_ids || target.layerTreeIds || (target.layer_tree_id ? [target.layer_tree_id] : []);
    if (targetTrees.length && (!tree || !targetTrees.map(String).includes(tree))) continue;
    if (activeLayerTree !== null && tree !== null && String(activeLayerTree) !== tree) continue;
    if (BEGIN_NAMES.has(name)) {
      const id = frameIdOf(event);
      if (id !== null && !beginById.has(id)) {
        const info = { id, start_ms: time, dropped: false, isPartial: false, idle: false, event };
        beginById.set(id, info); beginQueue.push(info);
      }
      continue;
    }
    if (DROP_NAMES.has(name)) {
      const id = frameIdOf(event);
      if (id !== null) {
        let info = beginById.get(id);
        if (!info) { info = { id, start_ms: time, dropped: true, isPartial: Boolean(dataOf(event).hasPartialUpdate || event.hasPartialUpdate), idle: false, event }; beginById.set(id, info); beginQueue.push(info); }
        info.dropped = true; info.isPartial = info.isPartial || Boolean(dataOf(event).hasPartialUpdate || event.hasPartialUpdate);
      }
      continue;
    }
    if (DRAW_NAMES.has(name)) {
      const id = frameIdOf(event);
      if (id === null || !beginById.has(id)) continue;
      while (beginQueue.length && String(beginQueue[0].id) !== id) {
        const old = beginQueue.shift(); beginById.delete(old.id);
        if (old.dropped) emit(old, null);
      }
      const info = beginById.get(id);
      if (info) {
        emit(info, info.event || event);
        mergeRow(rows.get(String(id)), event, target);
        beginById.delete(id); beginQueue.shift();
      }
      continue;
    }
    if (IDLE_NAMES.has(name)) {
      const id = frameIdOf(event);
      if (id !== null && beginById.has(id)) beginById.get(id).idle = true;
    }
  }
  const frames = [...rows.values()]
    .filter(row => row.start_ms !== null && row.start_ms >= startMs && row.start_ms < endMs)
    .sort((a, b) => a.start_ms - b.start_ms || a.id.localeCompare(b.id));
  const ambiguous = frames.some(row => row.ambiguous);
  const attributed = frames.filter(row => row.attribution === "game-canvas").length;
  return {
    ...parsed,
    frames,
    ambiguous,
    attributed,
    unparsed: false,
    errors: ambiguous ? ["ambiguous frame or canvas attribution"] : [],
  };
}

export function frameRows(payload, options = {}) {
  return buildFrameModel(payload, options).frames;
}

export function callbackTimes(callbacks) {
  if (!Array.isArray(callbacks)) return [];
  return callbacks.map(item => typeof item === "number" ? item : item?.timestamp_ms ?? item?.time_ms ?? item?.ts)
    .filter(value => typeof value === "number" && Number.isFinite(value)).sort((a, b) => a - b);
}

function ratio(count, denominator) {
  return denominator > 0 ? count / denominator : 0;
}

function failure(code, pointer, expected, observed) {
  return { code, pointer, expected, observed };
}

export function qualifyPerformance({ cell, trace, callbacks = [] }) {
  requireObject(cell, "/cell");
  const window = cell.window || {};
  const startMs = window.start_ms ?? cell.start_ms;
  const endMs = window.end_ms ?? cell.end_ms;
  if (typeof startMs !== "number" || typeof endMs !== "number" || !(endMs > startMs)) {
    return { status: "unverified", failures: [failure("missing-window", "/cell/window", "finite start_ms < end_ms", window)], metrics: {} };
  }
  const T = (endMs - startMs) / 1000;
  const parsed = parseTracePayload(trace);
  const failures = [];
  const completion = parsed.completion || {};
  if (parsed.format !== "fixture" && (completion.dataLossOccurred === undefined || !completion.stream)) {
    failures.push(failure("missing-completion-metadata", "/trace/completion", "dataLossOccurred and ReturnAsStream stream", completion));
  }
  if (parsed.dataLossOccurred === true || completion.dataLossOccurred === true) failures.push(failure("trace-data-loss", "/trace/completion/dataLossOccurred", false, true));
  if (parsed.unparsed) failures.push(failure("unparsed-format", "/trace/format", "trace-event-json", parsed.format));
  if (parsed.metadata?.clock_reconciled === false || parsed.metadata?.clock_match === false) failures.push(failure("clock-mismatch", "/trace/metadata/clock_reconciled", true, false));
  if (parsed.metadata?.window_start_ms !== undefined && parsed.metadata.window_start_ms > startMs) failures.push(failure("unpadded-window", "/trace/metadata/window_start_ms", `<= ${startMs}`, parsed.metadata.window_start_ms));
  if (parsed.metadata?.window_end_ms !== undefined && parsed.metadata.window_end_ms < endMs) failures.push(failure("unpadded-window", "/trace/metadata/window_end_ms", `>= ${endMs}`, parsed.metadata.window_end_ms));
  const target = cell.game_canvas || cell.target || {};
  const model = buildFrameModel(parsed, { target, startMs, endMs });
  if (model.ambiguous) failures.push(failure("ambiguous-attribution", "/trace/frames", "one game-canvas attribution", model.errors));
  const frames = model.frames;
  const targetFrames = frames.filter(row => row.attribution === "game-canvas");
  if (targetFrames.length === 0) failures.push(failure("missing-canvas-attribution", "/trace/frames", "at least one game-canvas frame", 0));
  const callback = callbackTimes(callbacks).filter(time => time >= startMs && time < endMs);
  const intervals = callback.slice(1).map((time, index) => time - callback[index]);
  const compliantIntervals = intervals.filter(value => value <= 18.33).length;
  const intervalRatio = intervals.length ? compliantIntervals / intervals.length : 0;
  const callbackRate = callback.length / T;
  const uniqueFlags = frames.filter(row => row.dropped || row.isPartial).length;
  const clean = targetFrames.filter(row => !row.idle && !row.dropped && !row.isPartial && row.draw);
  const frameTimes = clean.map(row => row.start_ms);
  const allGaps = [...callback, ...frameTimes].sort((a, b) => a - b).reduce((gaps, value, index, values) => {
    if (index) gaps.push(value - values[index - 1]);
    return gaps;
  }, []);
  const gapsFor = values => values.slice(1).map((value, index) => value - values[index]);
  // Callback cadence can continue while the target canvas stops drawing. The
  // frame series therefore gets its own stall test; merging both series would
  // hide exactly the negative case the qualification fixtures cover.
  const unexplainedStall = allGaps.some(value => value > 100)
    || gapsFor(targetFrames.map(row => row.start_ms)).some(value => value > 100)
    || gapsFor(callback).some(value => value > 100);
  const metrics = {
    window_start_ms: startMs,
    window_end_ms: endMs,
    duration_seconds: T,
    N: frames.length,
    C: clean.length,
    I: frames.filter(row => row.idle).length,
    D: uniqueFlags,
    callbacks: callback.length,
    callback_rate_hz: callbackRate,
    callback_interval_compliance: intervalRatio,
    max_callback_interval_ms: intervals.length ? Math.max(...intervals) : null,
    unexplained_stall: unexplainedStall,
    attribution: "game-canvas",
  };
  const mode = cell.mode || cell.surface || "animation";
  if (mode === "static" || mode === "static-idle") {
    return { status: failures.length ? "unverified" : "qualified", verdict: failures.length ? "performance: unverified" : "qualified", mode: "static", metrics: { ...metrics, fps_claim: false }, failures };
  }
  if (metrics.N <= 0) failures.push(failure("no-frames", "/metrics/N", "> 0", metrics.N));
  if (ratio(metrics.C, T) < 59) failures.push(failure("canvas-frame-floor", "/metrics/C", "C/T >= 59", `${metrics.C}/${T}`));
  if (ratio(metrics.D, metrics.N) > 0.01) failures.push(failure("dropped-partial-floor", "/metrics/D", "D/N <= 0.01", `${metrics.D}/${metrics.N}`));
  if (callbackRate < 59) failures.push(failure("callback-rate-floor", "/metrics/callback_rate_hz", ">= 59", callbackRate));
  if (intervalRatio < 0.99) failures.push(failure("callback-interval-floor", "/metrics/callback_interval_compliance", ">= 0.99", intervalRatio));
  if (unexplainedStall) failures.push(failure("unexplained-stall", "/metrics/unexplained_stall", false, true));
  return { status: failures.length ? "unverified" : "qualified", verdict: failures.length ? "performance: unverified" : "qualified", mode: "animation", metrics: { ...metrics, fps_claim: true }, failures };
}

export async function readReturnAsStream(client, handle) {
  requireString(handle, "/stream_handle");
  const chunks = [];
  let eof = false;
  while (!eof) {
    const reply = await client.send("IO.read", { handle });
    if (reply?.data) chunks.push(reply.base64Encoded ? Buffer.from(reply.data, "base64") : Buffer.from(reply.data));
    eof = reply?.eof === true;
  }
  try { await client.send("IO.close", { handle }); } catch { /* completion metadata remains useful */ }
  return Buffer.concat(chunks);
}

export async function collectCDPTrace(client, { durationMs = 1000, categories = ["devtools.timeline", "disabled-by-default-devtools.timeline.frame", "disabled-by-default-devtools.timeline.layers", "disabled-by-default-cc.debug", "cc"] } = {}) {
  const completionPromise = new Promise((resolve) => client.once?.("Tracing.tracingComplete", resolve));
  await client.send("Tracing.start", { transferMode: "ReturnAsStream", traceConfig: { includedCategories: categories } });
  await new Promise(resolve => setTimeout(resolve, durationMs));
  await client.send("Tracing.end");
  const completion = await completionPromise;
  if (!completion?.stream) throw inputError("CDP tracingComplete lacked ReturnAsStream handle", "/trace/completion/stream");
  const bytes = await readReturnAsStream(client, completion.stream);
  return {
    format: "cdp-return-as-stream",
    traceEvents: parseTracePayload(bytes).events,
    completion,
    raw_bytes: bytes.length,
    raw_stream_hash: sha256(bytes),
    transfer_mode: "ReturnAsStream",
  };
}
