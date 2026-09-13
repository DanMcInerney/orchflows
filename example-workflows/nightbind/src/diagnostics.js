import { BASE } from "./content.js";
import { SCENARIOS, createScenario } from "./scenarios.js";
import { snapshot, update, releaseAll, DT, candidates } from "./simulation.js";
export function installDiagnostics(ctx) {
  const variants = {
    default: {},
    "slow-charge": { chargeSeconds: 18 },
    "weak-evolution": { evolutionScale: 0.42 },
    "late-baseline": { lateWaveRate: 10 },
    "storm-route": { route: "storm" },
    "dusk-route": { route: "dusk" },
  };
  const adapter = {
    describe: () => ({
      version: 1,
      build: ctx.build,
      scenarios: SCENARIOS,
      fixedTick: DT,
      actions: ["move", "capture", "evolve", "dismiss", "pause", "keys"],
      coordinates: "x/right, z/down ground plane, arena radius19",
      stepRange: [1, 600],
      ready: true,
    }),
    snapshot: () => ({ ...snapshot(ctx.get()), build: ctx.build, ready: true }),
    reset({ seed = 12345, scenario = "fresh", variant = "default" } = {}) {
      if (
        !Number.isInteger(seed) ||
        !SCENARIOS.includes(scenario) ||
        !variants[variant]
      )
        throw Error("Invalid scenario/seed/variant");
      const mode = ctx.get().mode;
      ctx.replace(createScenario(seed, scenario, variants[variant]));
      ctx.get().mode = mode;
      ctx.render();
    },
    setMode(mode) {
      if (!["live", "manual"].includes(mode)) throw Error("Invalid mode");
      ctx.get().mode = mode;
      releaseAll(ctx.get());
      ctx.clearClock();
    },
    act(action) {
      return ctx.dispatch(action);
    },
    step(ticks) {
      if (
        ctx.get().mode !== "manual" ||
        !Number.isInteger(ticks) ||
        ticks < 1 ||
        ticks > 600
      )
        throw Error("Step requires manual mode and 1–600 ticks");
      for (let i = 0; i < ticks; i++) update(ctx.get(), DT);
      ctx.render();
    },
    releaseAll() {
      releaseAll(ctx.get());
      ctx.clearClock();
    },
  };
  window.__gameTest = Object.freeze(adapter);
  const box = document.createElement("details");
  box.className = "diag";
  box.innerHTML = `<summary>Development scenarios · assisted tests</summary><div><label>Scenario <select id="test-scenario">${SCENARIOS.map((s) => `<option>${s}</option>`).join("")}</select></label><label>Seed <input id="test-seed" type="number" value="12345"></label><label>Variant <select id="test-variant">${Object.keys(
    variants,
  )
    .map((s) => `<option>${s}</option>`)
    .join(
      "",
    )}</select></label><button id="test-reset">Reset scenario</button><label>Clock <select id="test-mode"><option>live</option><option>manual</option></select></label><button id="test-release">Release input</button><button id="test-start">Start scenario</button><div><label>Move x <input id="test-x" type="number" value="12"></label><label>z <input id="test-z" type="number" value="0"></label><button id="test-move">Move</button></div><div><label>Capture type <select id="test-capture-type">${BASE.map((t) => `<option>${t}</option>`).join("")}</select></label><button id="test-capture">Capture nearest of type</button></div><label>Ticks <input id="test-ticks" type="number" value="60" min="1" max="600"></label><button id="test-step">Step ticks</button><button id="test-observe">Refresh state</button><pre id="test-state"></pre></div>`;
  document.body.append(box);
  const $ = (id) => document.getElementById(id);
  function refresh() {
    const s = adapter.snapshot();
    $("test-state").textContent = JSON.stringify(
      { ...s, enemies: s.enemies.slice(0, 8) },
      null,
      2,
    );
    $("test-mode").value = s.mode;
  }
  $("test-reset").onclick = () => {
    adapter.reset({
      seed: Number($("test-seed").value),
      scenario: $("test-scenario").value,
      variant: $("test-variant").value,
    });
    refresh();
  };
  $("test-mode").onchange = () => {
    adapter.setMode($("test-mode").value);
    refresh();
  };
  $("test-start").onclick = () => {
    adapter.act({ type: "start" });
    ctx.render();
    refresh();
  };
  $("test-release").onclick = () => {
    adapter.releaseAll();
    refresh();
  };
  $("test-move").onclick = () => {
    adapter.act({
      type: "move",
      x: Number($("test-x").value),
      z: Number($("test-z").value),
    });
    refresh();
  };
  $("test-capture").onclick = () => {
    const c = candidates(ctx.get()).find(
      (c) => c.type === $("test-capture-type").value,
    );
    if (c) adapter.act({ type: "capture", id: c.id });
    refresh();
  };
  $("test-step").onclick = () => {
    try {
      adapter.step(Number($("test-ticks").value));
      refresh();
    } catch (e) {
      $("test-state").textContent = e.message;
    }
  };
  $("test-observe").onclick = refresh;
  refresh();
}
