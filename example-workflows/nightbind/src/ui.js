import { TYPES, RECIPES, WAVES } from "./content.js";
import { candidates, availableRecipes, releaseAll } from "./simulation.js";
import { waveGuidance } from "./encounters.js";
const portrait = (id, extra = "") => `<img class="portrait ${extra}" src="/models/portraits/${id}.png" width="48" height="48" alt="" draggable="false">`;
const hex = (c) => "#" + c.toString(16).padStart(6, "0");
const sigil = (t) =>
  ({
    ember: "◆",
    thorn: "✦",
    volt: "ϟ",
    mire: "♧",
    fang: "⟐",
    moth: "✧",
    pyre: "✺",
    storm: "ϟ",
    dusk: "☽",
    solar: "☀",
    world: "✵",
    eclipse: "◈",
  })[t];
export function createUI(root, game, dispatch, restart, build, { settings, saveSettings, audio }) {
  root.insertAdjacentHTML(
    "beforeend",
    `<div class="vignette"></div><div class="hud hidden" id="hud"><div class="topbar"><div class="brand">NIGHTBIND</div><div class="wave"><strong id="wave-label"></strong><small id="wave-name"></small><div class="wave-track" id="wave-track">${Array.from({ length: 12 }, () => "<span></span>").join("")}</div></div><div class="actions"><button class="quiet" id="guide-button">Field guide <span aria-hidden="true">↗</span></button><button class="quiet" id="pause-button">Pause</button><button class="quiet" id="settings-button" aria-label="Sound and motion settings">Settings</button></div></div><div class="health"><div class="health-label"><span>VITALITY</span><span id="health-value"></span></div><div class="bar"><i id="health-fill"></i></div><div class="hint" id="threat-count"></div></div><div class="bossbar hidden" id="bossbar">THE BELLKEEPER<div class="bar"><i id="boss-fill"></i></div></div><div class="toast" id="toast"></div><div class="wave-guidance" id="wave-guidance"></div><div class="controls-hint">Click ground to move · WASD / arrows · Space to bind</div><button class="evolve-call hidden" id="evolve-button">An evolution is ready ↗</button><div class="bottom"><div class="retinue"><div class="tiny retinue-label"><span>YOUR CIRCLE</span><span id="squad-count"></span></div><div class="slots" id="slots"></div></div><div class="capture"><div class="capture-head"><strong>Binding lantern</strong><span class="charge" id="charge-label"></span></div><div class="bar"><i id="charge-fill"></i></div><button class="gold" id="capture-button">Bind a creature</button><small>Choose one nearby foe · time pauses</small></div></div></div><div class="overlay" id="modal"></div><div class="build">${build}</div>`,
  );
  const $ = (id) => document.getElementById(id);
  let modal = "title",
    lastSquad = "",
    lastEvent = -1,
    toastAt = 0,
    hoveredCapture = null,
    captureViewportWidth = 0;
  function setModal(kind, html) {
    document.querySelector(".diag")?.removeAttribute("open");
    modal = kind;
    hoveredCapture = null;
    $("modal").classList.toggle("capture-mode", kind === "capture");
    $("modal").innerHTML = html;
    $("modal").classList.remove("hidden");
    if (kind === "capture") {
      $("modal").insertAdjacentHTML(
        "afterbegin",
        '<div class="planning-caption"><strong>LANTERN VIEW</strong><span>Your keeper is centered. The gold circle marks your reach.</span></div>',
      );
      captureViewportWidth = Math.max(
        1,
        document.querySelector("#modal .panel").getBoundingClientRect().left -
          16,
      );
    } else captureViewportWidth = 0;
    if (game().phase === "playing") {
      game().paused = true;
      releaseAll(game());
    }
    document.querySelector("#modal button")?.focus();
  }
  function close() {
    modal = null;
    hoveredCapture = null;
    captureViewportWidth = 0;
    $("modal").classList.add("hidden");
    if (game().phase === "playing") game().paused = false;
    document.querySelector("canvas")?.focus();
  }
  function title() {
    setModal(
      "title",
      `<section class="panel title-panel"><div class="intro"><div><div class="eyebrow">A LANTERN AGAINST THE DARK</div><div class="title-mark"><h1>NIGHT<br>BIND</h1>${portrait("keeper", "title-portrait")}</div><p class="promise">The horde is your enemy.<br>And your only hope.</p><p>Capture the creatures closing in. Build a circle of monsters. Evolve them into something the night should fear.</p><button class="gold" id="start-button">Light the lantern <span aria-hidden="true">→</span></button></div><div class="intro-art"><div class="eyebrow">ONE NIGHT · TWELVE WAVES</div><div class="steps"><div class="step"><b>01</b><div><strong>Move. Your lantern and circle fight.</strong><p>Click the ground or use WASD / arrows. Your lantern fires automatically; companions add their own attacks.</p></div></div><div class="step"><b>02</b><div><strong>Bind a real creature every 11 seconds.</strong><p>Open the lantern, choose a nearby foe. Planning pauses time. Six places in your circle.</p></div></div><div class="step"><b>03</b><div><strong>Plan your two awakenings.</strong><p>Combine a pair at wave 5. Add two matching companions to ascend at wave 10. The Field guide shows every recipe.</p></div></div><div class="step"><b>12</b><div><strong>Bring down the Bellkeeper.</strong><p>Survive one continuous run, about five minutes. Good captures turn desperate crowds into a moment of power.</p></div></div></div><button class="quiet" id="title-guide">Read the evolution recipes</button><button class="quiet" id="title-settings">Sound & motion</button></div></div><div class="intro-footer"><span>KEYBOARD + POINTER · DESKTOP PLAY</span><span>Original creatures. Earned power.</span></div></section>`,
    );
    $("start-button").onclick = () => {
      close();
      dispatch({ type: "start" });
    };
    $("title-guide").onclick = () => guide();
    $("title-settings").onclick = preferences;
  }
  function recipeCard(r, s) {
    const t = TYPES[r.result],
      has = r.needs.every((n) => s.squad.some((a) => a.type === n));
    const second = RECIPES.find((n) => n.needs[0] === r.result);
    const names = (needs) =>
      needs
        .map(
          (n) =>
            `<span class="${s.squad.some((a) => a.type === n) ? "owned" : ""}">${portrait(n, "ingredient-portrait")}${TYPES[n].name}</span>`,
        )
        .join(" + ");
    return `<article class="recipe"><div class="tiny">WAVE ${r.wave} · FIRST AWAKENING</div>${portrait(r.result, "recipe-portrait")}<h3 style="margin-top:8px">${t.name}</h3><div class="ingredients">${names(r.needs)}</div><p>${t.tip}.</p>${s.phase === "playing" ? `<button data-evolve="${r.result}" ${!has || s.wave < r.wave ? "disabled" : ""}>${s.wave < r.wave ? "Unlocks at wave 5" : has ? "Awaken " + t.name : "Gather the pair"}</button>` : ""}<div class="tier2"><div class="tiny">WAVE 10 · ASCENSION</div>${portrait(second.result, "recipe-portrait")}<h3 style="margin-top:8px">${TYPES[second.result].name}</h3><div class="ingredients">${names(second.needs)}</div><p>${TYPES[second.result].tip}.</p>${s.phase === "playing" ? `<button data-evolve="${second.result}" ${!availableRecipes(s).some((x) => x.result === second.result) ? "disabled" : ""}>${s.wave < 10 ? "Unlocks at wave 10" : availableRecipes(s).some((x) => x.result === second.result) ? "Ascend" : "Gather the companions"}</button>` : ""}</div></article>`;
  }
  function guide() {
    const s = game();
    setModal(
      "guide",
      `<section class="panel"><div class="modal-head"><div><div class="eyebrow">THE FIELD GUIDE</div><h2>Choose who you become.</h2></div><button id="close-modal">${s.phase === "title" ? "Back" : "Return to the night"}</button></div><p class="guide-focus">${s.phase === "playing" ? waveGuidance(s) : "Every creature has a role. A carefully chosen circle can turn the horde."}</p><p>Captures become allies immediately. An evolution consumes its ingredients, frees space and restores 25 vitality. You may awaken more than one pair. Green names are already in your circle.</p><div class="recipe-grid">${RECIPES.filter(
        (r) => r.wave === 5,
      )
        .map((r) => recipeCard(r, s))
        .join(
          "",
        )}</div><p>Thornbacks blunt incoming damage. Mirelings slow crowds. Moths restore vitality. Fanglings target the strongest foe. Emberlings punish groups; Voltwings catch scattered enemies.</p>${s.phase === "playing" ? `<div class="tiny">RELEASE A COMPANION TO MAKE ROOM</div><div class="release-list">${s.squad.map((a) => `<button data-dismiss="${a.id}">Release ${TYPES[a.type].name}</button>`).join("") || "<p>Your circle is empty.</p>"}</div>` : ""}</section>`,
    );
    $("close-modal").onclick = () => (s.phase === "title" ? title() : close());
    document.querySelectorAll("[data-evolve]").forEach(
      (b) =>
        (b.onclick = () => {
          dispatch({ type: "evolve", result: b.dataset.evolve });
          close();
        }),
    );
    document.querySelectorAll("[data-dismiss]").forEach(
      (b) =>
        (b.onclick = () => {
          dispatch({ type: "dismiss", id: Number(b.dataset.dismiss) });
          guide();
        }),
    );
  }
  function capture() {
    const s = game();
    if (s.phase !== "playing" || s.charge < 1) return;
    const list = candidates(s);
    setModal(
      "capture",
      `<section class="panel"><div class="modal-head"><div><div class="eyebrow">THE LANTERN IS OPEN · TIME IS STILL</div><h2>Who will fight beside you?</h2></div><button id="close-modal">Cancel</button></div><p>Bind one living creature within lantern reach. Your next charge takes ${s.config.chargeSeconds} seconds. ${s.squad.length >= 6 ? "Your circle is full. Release a companion in the Field guide first." : "The gold circle marks your reach. Hover or focus a choice to locate the creature. Choose for now — and for your evolution."}</p><div class="capture-grid">${
        list
          .map((c) => {
            const t = TYPES[c.type];
            return `<button class="creature-card" data-capture="${c.id}" ${s.squad.length >= 6 ? "disabled" : ""}>${portrait(c.type, "capture-portrait")}<span class="tiny" style="color:${hex(t.color)}">${sigil(c.type)} ${t.role} · ${c.count} IN REACH</span><strong>${t.name}</strong><small>${t.tip}</small></button>`;
          })
          .join("") ||
        "<p>No creature is within lantern reach. Move closer to a living enemy and open the lantern again.</p>"
      }</div><div style="display:flex;justify-content:space-between;margin-top:20px"><button class="quiet" id="capture-guide">Consult the recipes</button><span class="tiny" style="align-self:center">${s.squad.length} / 6 COMPANIONS</span></div></section>`,
    );
    $("close-modal").onclick = close;
    $("capture-guide").onclick = guide;
    document.querySelectorAll("[data-capture]").forEach((b) => {
      b.onmouseenter = b.onfocus = () => {
        hoveredCapture = Number(b.dataset.capture);
      };
      b.onmouseleave = b.onblur = () => {
        hoveredCapture = null;
      };
    });
    document.querySelectorAll("[data-capture]").forEach(
      (b) =>
        (b.onclick = () => {
          dispatch({ type: "capture", id: Number(b.dataset.capture) });
          close();
        }),
    );
  }
  function pause() {
    const s = game();
    if (s.phase !== "playing") return;
    setModal(
      "pause",
      `<section class="panel result"><div class="eyebrow">THE NIGHT CAN WAIT</div><h2>Take a breath.</h2><p>Your lantern, enemies and wave timer are paused.</p><button class="gold" id="resume">Return to the night</button><button class="quiet" id="restart">Start a new run</button></section>`,
    );
    $("resume").onclick = close;
    $("restart").onclick = () => {
      close();
      restart();
      title();
    };
  }
  function preferences() {
    const s = game();
    setModal("settings", `<section class="panel result settings-panel"><div class="eyebrow">MAKE ROOM FOR THE NIGHT</div><h2>Sound & motion</h2><label class="settings-row" for="sound-muted"><span>Mute sound</span><input id="sound-muted" type="checkbox" ${settings.muted ? "checked" : ""}></label><label class="settings-row" for="sound-volume"><span>Volume <output id="volume-value">${Math.round(settings.volume * 100)}%</output></span><input id="sound-volume" type="range" min="0" max="100" value="${settings.volume * 100}"></label><label class="settings-row" for="reduced-motion"><span>Reduce decorative motion</span><input id="reduced-motion" type="checkbox" ${settings.reducedMotion ? "checked" : ""}></label><p>Threat warnings and essential feedback remain visible. Preferences are saved on this browser; runs begin fresh.</p><p class="tiny" id="audio-status"></p><button class="gold" id="settings-close">${s.phase === "title" ? "Back to title" : "Return to the night"}</button></section>`);
    const apply = () => {
      settings.muted = $("sound-muted").checked;
      settings.volume = Number($("sound-volume").value) / 100;
      settings.reducedMotion = $("reduced-motion").checked;
      $("volume-value").textContent = `${Math.round(settings.volume * 100)}%`;
      saveSettings(); audio.apply();
    };
    for (const id of ["sound-muted", "sound-volume", "reduced-motion"]) $(id).oninput = apply;
    const describe = audio.describe();
    $("audio-status").textContent = describe.error || "Original bell, glass and low drum cues.";
    $("settings-close").onclick = () => s.phase === "title" ? title() : close();
  }
  function outcome() {
    const s = game(),
      won = s.phase === "won";
    setModal(
      "outcome",
      `<section class="panel result"><div class="eyebrow">${won ? "THE TWELFTH BELL FALLS SILENT" : "THE CIRCLE IS BROKEN"}</div><h2>${won ? "You brought the dawn." : "The lantern goes dark."}</h2><p>${won ? "What hunted you became your greatest strength. The Bellkeeper has fallen." : "The night closes in. A different capture can change everything."}</p><div class="outcome-circle">${s.squad.map((a) => portrait(a.type)).join("")}</div><div class="results-grid"><div><strong>${s.wave}</strong><small>WAVES REACHED</small></div><div><strong>${s.kills}</strong><small>FOES FALLEN</small></div><div><strong>${s.stats.evolutions.length}</strong><small>EVOLUTIONS</small></div></div><p>${s.stats.evolutions.length ? s.stats.evolutions.map((e) => TYPES[e.result].name).join(" → ") : "Try Emberling + Thornback for a protective first awakening."}</p><button class="gold" id="retry">Light another lantern</button><button class="quiet" id="outcome-guide">Study the recipes</button></section>`,
    );
    $("retry").onclick = () => {
      restart();
      close();
      dispatch({ type: "start" });
    };
    $("outcome-guide").onclick = guide;
  }
  $("capture-button").onclick = capture;
  $("guide-button").onclick = guide;
  $("pause-button").onclick = pause;
  $("settings-button").onclick = preferences;
  $("evolve-button").onclick = guide;
  function update() {
    const s = game();
    $("hud").classList.toggle("hidden", s.phase === "title");
    $("wave-label").textContent =
      `WAVE ${String(s.wave).padStart(2, "0")} / 12`;
    $("wave-name").textContent = WAVES[s.wave - 1][0];
    $("wave-guidance").textContent = waveGuidance(s);
    $("wave-guidance").style.opacity =
      s.phase === "playing" && s.time % s.config.waveSeconds < 7 ? "1" : "0";
    [...$("wave-track").children].forEach((e, i) =>
      e.classList.toggle("passed", i < s.wave),
    );
    $("health-value").textContent = `${Math.ceil(s.hp)} / ${s.maxHp}`;
    $("health-fill").style.width = `${(s.hp / s.maxHp) * 100}%`;
    $("threat-count").textContent =
      `${s.enemies.length} in the dark · ${s.kills} fallen`;
    $("charge-label").textContent =
      s.charge >= 1
        ? "READY"
        : `${Math.ceil((1 - s.charge) * s.config.chargeSeconds)}s`;
    $("charge-fill").style.width = `${s.charge * 100}%`;
    $("capture-button").disabled = s.charge < 1;
    $("capture-button").textContent =
      s.charge >= 1 ? "Bind a creature" : "Lantern is gathering light";
    $("squad-count").textContent = `${s.squad.length} / 6`;
    const signature = s.squad.map((a) => a.type).join(",");
    if (lastSquad !== signature || !$("slots").children.length) {
      lastSquad = signature;
      $("slots").innerHTML = Array.from({ length: 6 }, (_, i) =>
        s.squad[i]
          ? `<div class="slot">${portrait(s.squad[i].type)}<span class="name">${TYPES[s.squad[i].type].name}</span><span class="role">${TYPES[s.squad[i].type].role}</span></div>`
          : '<div class="slot empty">·</div>',
      ).join("");
    }
    const boss = s.enemies.find((e) => e.type === "boss");
    $("bossbar").classList.toggle("hidden", !boss);
    if (boss) $("boss-fill").style.width = `${(boss.hp / boss.maxHp) * 100}%`;
    $("evolve-button").classList.toggle("hidden", !availableRecipes(s).length);
    const latest = [...s.events]
      .reverse()
      .find((e) => ["evolve", "wave", "capture", "boss"].includes(e.type));
    if (!latest) {
      $("toast").textContent = "";
      lastEvent = -1;
    }
    if (latest && latest.tick !== lastEvent) {
      lastEvent = latest.tick;
      toastAt = s.time;
      $("toast").innerHTML = latest.type === "evolve"
        ? `${portrait(latest.result, "awakening-portrait")}<div><small>${TYPES[latest.result].tier === 2 ? "ASCENSION" : "FIRST AWAKENING"}</small><span>${latest.text}</span></div>`
        : latest.type === "capture" ? `${portrait(latest.creature)}<span>${latest.text}</span>` : latest.text;
      $("toast").classList.toggle("awakening", latest.type === "evolve");
    }
    $("toast").style.opacity = s.time - toastAt < 3 ? "1" : "0";
    document.querySelector(".vignette").classList.toggle("hurt", s.invuln > 0 && !settings.reducedMotion);
    if (
      (s.phase === "won" || s.phase === "lost") &&
      modal !== "outcome" &&
      modal !== "guide"
    )
      outcome();
    if (s.waveNotice && !modal) {
      s.waveNotice = 0;
      guide();
    }
  }
  addEventListener("resize", () => {
    if (modal === "capture")
      captureViewportWidth = Math.max(
        1,
        document.querySelector("#modal .panel").getBoundingClientRect().left -
          16,
      );
  });
  title();
  return {
    update,
    title,
    close,
    capture,
    guide,
    pause,
    get captureViewportWidth() {
      return captureViewportWidth;
    },
    get hoveredCapture() {
      return hoveredCapture;
    },
    get modal() {
      return modal;
    },
  };
}
