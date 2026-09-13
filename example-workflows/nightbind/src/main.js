import "./style.css";
import {
  createGame,
  act,
  update,
  snapshot,
  releaseAll,
  DT,
} from "./simulation.js";
import { createView } from "./view.js";
import { createUI } from "./ui.js";
import { settings, saveSettings } from "./settings.js";
import { createAudio } from "./audio.js";
const BUILD = import.meta.env.VITE_BUILD_ID || "development";
const audio = createAudio(settings);
let state = createGame(), accumulator = 0, last = 0, frameTotal = 0, run = 1;
const frameHistory = [], HISTORY_LIMIT = 24000;
let historyHead = 0;
const loadStarted = performance.now();
const app = document.querySelector("#app");
app.innerHTML = '<div id="world"></div><div class="overlay" id="loading"><section class="panel loading-panel"><div class="eyebrow">THE BELL COURT IS WAKING</div><h1>NIGHTBIND</h1><p id="loading-status" role="status">Opening the binding lantern…</p><progress id="loading-progress" max="22" value="0"></progress></section></div><script type="application/json" id="game-observation">{"ready":false,"phase":"loading"}</script><script type="application/json" id="performance-observation"></script>';
let view;
try {
  view = await createView(document.querySelector("#world"), { settings, onProgress: (done, total, id) => {
    document.querySelector("#loading-status").textContent = `Preparing ${id.replaceAll("_", " ")} · ${done} / ${total}`;
    document.querySelector("#loading-progress").value = done;
  } });
} catch (error) {
  document.querySelector("#loading").innerHTML = '<section class="panel loading-panel"><div class="eyebrow">THE LANTERN COULD NOT BE LIT</div><h2>The court is out of reach.</h2><p>Check the connection and graphics acceleration, then try again.</p><p id="load-error" role="alert"></p><button class="gold" id="load-retry">Try loading again</button></section>';
  document.querySelector("#load-error").textContent = error.message;
  document.querySelector("#load-retry").onclick = () => location.reload();
  document.querySelector("#game-observation").textContent = JSON.stringify({ ready: false, phase: "error", error: error.message, build: BUILD });
  throw error;
}
const readyAtMs = performance.now(), loadDurationMs = readyAtMs - loadStarted;
document.querySelector("#loading").remove();
function replaceState(next) { state = next; accumulator = 0; last = 0; run++; return state; }
function reset() { return replaceState(createGame()); }
function dispatch(action) { return act(state, action); }
const ui = createUI(app, () => state, dispatch, reset, BUILD, { settings, saveSettings, audio });
for (const type of ["pointerdown", "keydown"]) document.addEventListener(type, () => audio.unlock(), { capture: true });
view.canvas.addEventListener("webglcontextlost", (event) => {
  event.preventDefault(); state.paused = true; releaseAll(state); view.renderer.setAnimationLoop(null);
  const dialog = document.createElement("div"); dialog.className = "overlay";
  dialog.innerHTML = '<section class="panel result"><h2>The light went out.</h2><p>The graphics context was interrupted. Reload to start a fresh run.</p><button id="graphics-retry">Reload Nightbind</button></section>';
  app.append(dialog); document.querySelector("#graphics-retry").onclick = () => location.reload();
});
const held = new Set();
function keyIntent() {
  dispatch({
    type: "keys",
    x:
      (held.has("d") || held.has("arrowright") ? 1 : 0) -
      (held.has("a") || held.has("arrowleft") ? 1 : 0),
    z:
      (held.has("s") || held.has("arrowdown") ? 1 : 0) -
      (held.has("w") || held.has("arrowup") ? 1 : 0),
  });
}
view.canvas.addEventListener("pointerdown", (e) => {
  if (state.phase !== "playing" || ui.modal) return;
  view.canvas.focus();
  held.clear();
  dispatch({ type: "move", ...view.point(e.clientX, e.clientY) });
});
document.addEventListener("keydown", (e) => {
  if (e.target.matches("input,select,textarea")) return;
  const k = e.key.toLowerCase();
  if (k === "escape") {
    if (state.phase === "title") ui.title();
    else ui.modal ? ui.close() : ui.pause();
    held.clear();
    return;
  }
  if (ui.modal || (k === " " && e.target.closest("button"))) return;
  if ([" ", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(k))
    e.preventDefault();
  if (e.repeat) return;
  if (k === " ") {
    ui.capture();
    held.clear();
    return;
  }
  if (k === "e") {
    ui.guide();
    return;
  }
  if (
    [
      "w",
      "a",
      "s",
      "d",
      "arrowup",
      "arrowdown",
      "arrowleft",
      "arrowright",
    ].includes(k)
  ) {
    held.add(k);
    keyIntent();
  }
});
document.addEventListener("keyup", (e) => {
  const k = e.key.toLowerCase();
  if (
    ![
      "w",
      "a",
      "s",
      "d",
      "arrowup",
      "arrowdown",
      "arrowleft",
      "arrowright",
    ].includes(k)
  )
    return;
  held.delete(k);
  if (!ui.modal) keyIntent();
});
function focusLost() {
  held.clear();
  releaseAll(state);
  accumulator = 0;
  last = 0;
  if (state.phase === "playing" && !ui.modal) ui.pause();
}
window.addEventListener("blur", focusLost);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) focusLost();
});
let frame = 0;
view.renderer.setAnimationLoop((now) => {
  const rawElapsed = last ? (now - last) / 1000 : 0;
  const elapsed = Math.min(rawElapsed, 0.2);
  last = now;
  if (state.mode === "live" && !state.paused) {
    accumulator += elapsed;
    let loops = 0;
    while (accumulator >= DT && loops++ < 8) {
      update(state, DT);
      accumulator -= DT;
    }
    if (loops >= 8) accumulator = 0;
  } else accumulator = 0;
  view.render(state, ui.modal, ui.hoveredCapture, ui.captureViewportWidth);
  audio.update(state);
  if (frame++ % 6 === 0) {
    ui.update();
    document.querySelector("#game-observation").textContent = JSON.stringify({
      ...snapshot(state),
      presentation: {
        modal: ui.modal,
        highlightedCaptureId: ui.hoveredCapture,
        captureViewportWidth: ui.captureViewportWidth,
      },
      build: BUILD,
      ready: true,
      run,
      assets: { loaded: view.assets.count },
      settings: { ...settings },
      audio: audio.describe(),
    });
  }
  if (
    state.phase === "playing" &&
    !state.paused &&
    state.mode === "live" &&
    rawElapsed > 0
  ) {
    const sample = [run, +state.time.toFixed(3), state.wave, state.enemies.length, +(rawElapsed * 1000).toFixed(3), view.renderer.info.render.calls, view.renderer.info.render.triangles];
    if (frameHistory.length < HISTORY_LIMIT) frameHistory.push(sample);
    else { frameHistory[historyHead] = sample; historyHead = (historyHead + 1) % HISTORY_LIMIT; }
    frameTotal++;
  }
  if (frame % 60 === 0)
    document.querySelector("#performance-observation").textContent =
      JSON.stringify(readPerformance());
});
// Read-only observables are available in both builds. Mutating test operations are dev-only.
function readPerformance() {
  const gl = view.renderer.getContext(),
    ext = gl.getExtension("WEBGL_debug_renderer_info");
  return {
    build: BUILD,
    fields: ["run", "time", "wave", "hostiles", "rawFrameMs", "calls", "triangles"],
    frames: [...frameHistory.slice(historyHead), ...frameHistory.slice(0, historyHead)],
    readyAtMs, loadDurationMs, run,
    assets: view.assets,
    total: frameTotal,
    viewport: {
      width: innerWidth,
      height: innerHeight,
      dpr: view.renderer.getPixelRatio(),
    },
    renderer: view.renderer.info.render,
    resources: view.renderer.info.memory,
    backend: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unavailable",
    time: state.time,
    hostiles: state.enemies.length,
  };
}
Object.defineProperty(window, "nightbind", {
  value: Object.freeze({
    snapshot: () => ({ ...snapshot(state), build: BUILD, ready: true }),
    performance: readPerformance,
  }),
  writable: false,
});
if (import.meta.env.DEV || import.meta.env.VITE_TEST_BUILD === "1") {
  import("./diagnostics.js").then(({ installDiagnostics }) =>
    installDiagnostics({
      get: () => state,
      replace: (next) => {
        ui.close();
        return replaceState(next);
      },
      dispatch,
      render: () => {
        view.render(
          state,
          ui.modal,
          ui.hoveredCapture,
          ui.captureViewportWidth,
        );
        ui.update();
      },
      clearClock: () => {
        accumulator = 0;
        last = 0;
        held.clear();
      },
      build: BUILD,
    }),
  );
}
window.addEventListener("pagehide", () => {
  releaseAll(state);
  audio.dispose();
  view.dispose();
});
