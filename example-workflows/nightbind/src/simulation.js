import { TYPES, BASE, RECIPES, WAVES, DEFAULTS } from "./content.js";
export const DT = 1 / 60;
const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
export function createGame(seed = 12345, config = {}) {
  const s = {
    version: 1,
    seed,
    rng: seed >>> 0,
    scenario: "fresh",
    config: { ...DEFAULTS, ...config },
    tick: 0,
    time: 0,
    wave: 1,
    phase: "title",
    paused: false,
    mode: "live",
    charge: 1,
    hp: 120,
    maxHp: 120,
    player: { x: 0, z: 0 },
    target: null,
    keys: { x: 0, z: 0 },
    squad: [],
    enemies: [],
    shots: [],
    zones: [],
    effects: [],
    events: [],
    kills: 0,
    nextId: 1,
    spawnClock: 0,
    bolt: 0,
    invuln: 0,
    healClock: 0,
    waveNotice: 0,
    bossSpawned: false,
    bossDefeated: false,
    stats: { captures: 0, evolutions: [], damageTaken: 0, damageBy: {} },
  };
  return s;
}
export function rand(s) {
  s.rng = (Math.imul(s.rng, 1664525) + 1013904223) >>> 0;
  return s.rng / 4294967296;
}
export function event(s, type, text, data = {}) {
  s.events.push({ tick: s.tick, type, text, ...data });
  if (s.events.length > 60) s.events.shift();
}
export function spawnEnemy(s, type, radius = 20) {
  const a = rand(s) * Math.PI * 2,
    t = TYPES[type];
  const e = {
    id: s.nextId++,
    type,
    x: Math.cos(a) * radius,
    z: Math.sin(a) * radius,
    hp: t.hp * (1 + (s.wave - 1) * 0.11),
    maxHp: t.hp * (1 + (s.wave - 1) * 0.11),
    clock: rand(s) * 2,
    slow: 0,
    wind: 0,
    dx: 0,
    dz: 0,
  };
  if (type === "boss") {
    e.hp = e.maxHp = TYPES.boss.hp;
    e.x = 0;
    e.z = -12;
    e.clock = 3;
  }
  s.enemies.push(e);
  return e;
}
export function releaseAll(s) {
  s.keys = { x: 0, z: 0 };
  s.target = null;
}
export function candidates(s) {
  return BASE.map((type) => ({
    type,
    enemies: s.enemies.filter(
      (e) => e.type === type && distance(e, s.player) <= s.config.captureRange,
    ),
  }))
    .filter((x) => x.enemies.length)
    .map((x) => ({
      type: x.type,
      count: x.enemies.length,
      id: x.enemies.sort(
        (a, b) => distance(a, s.player) - distance(b, s.player),
      )[0].id,
    }));
}
export function availableRecipes(s) {
  return RECIPES.filter(
    (r) =>
      s.wave >= r.wave &&
      r.needs.every((t) => s.squad.some((a) => a.type === t)),
  );
}
export function act(s, a) {
  switch (a.type) {
    case "start":
      if (s.phase === "title") {
        s.phase = "playing";
        event(s, "start", "The lantern is lit.");
      }
      return;
    case "pause":
      if (s.phase === "playing") {
        s.paused = !s.paused;
        releaseAll(s);
      }
      return;
    case "move":
      if (Number.isFinite(a.x) && Number.isFinite(a.z)) {
        s.target = { x: clamp(a.x, -19, 19), z: clamp(a.z, -19, 19) };
        s.keys = { x: 0, z: 0 };
      }
      return;
    case "keys":
      s.keys = { x: clamp(a.x || 0, -1, 1), z: clamp(a.z || 0, -1, 1) };
      s.target = null;
      return;
    case "capture": {
      if (s.phase !== "playing" || s.charge < 1 || s.squad.length >= 6)
        return false;
      const e = s.enemies.find(
        (e) =>
          e.id === a.id &&
          e.type !== "boss" &&
          distance(e, s.player) <= s.config.captureRange,
      );
      if (!e) return false;
      s.enemies = s.enemies.filter((x) => x !== e);
      s.squad.push({ id: s.nextId++, type: e.type, clock: 0 });
      s.charge = 0;
      s.stats.captures++;
      s.effects.push({
        kind: "bind",
        x: e.x,
        z: e.z,
        color: TYPES[e.type].color,
        life: 1,
        max: 1,
        r: 2,
      });
      event(s, "capture", `${TYPES[e.type].name} joins your circle.`, {
        creature: e.type,
      });
      return true;
    }
    case "dismiss":
      if (Number.isInteger(a.id)) {
        s.squad = s.squad.filter((x) => x.id !== a.id);
        event(s, "dismiss", "A companion was released.");
      }
      return;
    case "evolve": {
      const r = availableRecipes(s).find((r) => r.result === a.result);
      if (!r) return false;
      for (const type of r.needs) {
        const i = s.squad.findIndex((x) => x.type === type);
        s.squad.splice(i, 1);
      }
      s.squad.push({ id: s.nextId++, type: r.result, clock: 0 });
      s.hp = Math.min(s.maxHp, s.hp + 25);
      s.stats.evolutions.push({ wave: s.wave, time: s.time, result: r.result });
      s.effects.push({
        kind: "evolve",
        x: s.player.x,
        z: s.player.z,
        color: TYPES[r.result].color,
        life: 2,
        max: 2,
        r: 16,
      });
      event(s, "evolve", `${TYPES[r.result].name} awakens.`, {
        result: r.result,
      });
      return true;
    }
    default:
      throw Error("Unsupported action");
  }
}
function hurt(s, amount) {
  if (s.invuln > 0) return;
  const ward = s.squad.some((a) => ["thorn", "pyre", "solar"].includes(a.type));
  const taken = amount * (ward ? 0.58 : 1);
  s.hp = Math.max(0, s.hp - taken);
  s.stats.damageTaken += taken;
  s.invuln = 0.6;
  event(s, "damage", `Lost ${Math.round(taken)} vitality.`);
  s.effects.push({
    kind: "hurt",
    x: s.player.x,
    z: s.player.z,
    color: 0xf1747d,
    life: 0.4,
    max: 0.4,
    r: 1.8,
  });
}
function damage(s, e, power, source) {
  if (e.hp <= 0) return;
  e.hp -= power;
  s.stats.damageBy[source] =
    (s.stats.damageBy[source] || 0) + Math.min(power, e.hp + power);
  if (e.hp <= 0) {
    s.kills++;
    if (e.type === "boss") {
      s.bossDefeated = true;
      event(s, "boss", "The Bellkeeper falls.");
    }
    if (rand(s) < 0.035) {
      s.hp = Math.min(s.maxHp, s.hp + 1.5);
    }
  }
}
function area(s, p, r, power, source, slow = 0) {
  for (const e of s.enemies)
    if (distance(e, p) <= r) {
      damage(s, e, power, source);
      e.slow = Math.max(e.slow, slow);
    }
  s.effects.push({
    kind: "ring",
    x: p.x,
    z: p.z,
    color: TYPES[source]?.color || 0xeed2a4,
    life: 0.45,
    max: 0.45,
    r,
  });
}
function allyAttack(s, a) {
  const t = TYPES[a.type];
  const near = s.enemies
    .filter((e) => e.hp > 0 && distance(e, s.player) < t.range)
    .sort((a, b) => distance(a, s.player) - distance(b, s.player));
  if (!near.length) return;
  let power = t.power * (t.tier ? s.config.evolutionScale : 1),
    target = near[0];
  if (["fang", "dusk", "eclipse"].includes(a.type))
    target = [...near].sort((a, b) => b.maxHp - a.maxHp)[0];
  if (a.type === "ember") area(s, target, 2.7, power, a.type);
  else if (a.type === "thorn") {
    area(s, s.player, 5, power, a.type);
    for (const e of near.slice(0, 10)) {
      const d = distance(e, s.player) || 1;
      e.x += ((e.x - s.player.x) / d) * 1.5;
      e.z += ((e.z - s.player.z) / d) * 1.5;
    }
  } else if (["volt", "storm", "world"].includes(a.type)) {
    const count = a.type === "volt" ? 3 : a.type === "storm" ? 10 : 30;
    for (const e of near.slice(0, count)) {
      damage(s, e, power, a.type);
      e.slow = a.type === "volt" ? 0 : 1.8;
      s.effects.push({
        kind: "beam",
        x: s.player.x,
        z: s.player.z,
        tx: e.x,
        tz: e.z,
        color: t.color,
        life: 0.22,
        max: 0.22,
        r: 1,
      });
    }
  } else if (a.type === "mire") {
    area(s, target, 3.6, power, a.type, 2.8);
  } else if (a.type === "pyre") area(s, target, 6.5, power, a.type, 0.4);
  else if (a.type === "solar") {
    area(s, s.player, 17, power, a.type, 1);
    s.hp = Math.min(s.maxHp, s.hp + 3);
  } else if (a.type === "eclipse") {
    area(s, target, 9, power, a.type, 1);
    s.hp = Math.min(s.maxHp, s.hp + 2);
  } else {
    damage(s, target, power, a.type);
    s.effects.push({
      kind: "beam",
      x: s.player.x,
      z: s.player.z,
      tx: target.x,
      tz: target.z,
      color: t.color,
      life: 0.25,
      max: 0.25,
      r: 1,
    });
    if (a.type === "dusk") {
      area(s, target, 3, power * 0.3, a.type);
      s.hp = Math.min(s.maxHp, s.hp + 3);
    }
    if (a.type === "moth") s.hp = Math.min(s.maxHp, s.hp + 4);
  }
}
function attackEnemies(s, dt) {
  for (const e of s.enemies) {
    if (e.hp <= 0) continue;
    const t = TYPES[e.type],
      d = distance(e, s.player) || 0.001;
    const ux = (s.player.x - e.x) / d,
      uz = (s.player.z - e.z) / d;
    e.clock -= dt;
    e.slow = Math.max(0, e.slow - dt);
    let speed = t.speed * (e.slow > 0 ? 0.35 : 1);
    if (e.type === "mire" && d < 10) {
      speed = d < 7 ? -1.3 : 0;
      if (e.clock <= 0) {
        s.zones.push({
          x: s.player.x,
          z: s.player.z,
          r: 2.3,
          wind: 1.3,
          life: 4,
          power: 9,
        });
        e.clock = 4.5;
      }
    }
    if (e.type === "moth") {
      speed = d < 9 ? 0 : speed;
      if (e.clock <= 0) {
        for (const other of s.enemies)
          if (other.hp > 0 && distance(e, other) < 4)
            other.hp = Math.min(other.maxHp, other.hp + 8);
        s.effects.push({
          kind: "ring",
          x: e.x,
          z: e.z,
          color: t.color,
          life: 0.4,
          max: 0.4,
          r: 4,
        });
        e.clock = 5;
      }
    }
    if (e.type === "volt") {
      speed *= 0.85;
      e.x += Math.cos(s.time * 2 + e.id) * dt * 1.1;
      e.z += Math.sin(s.time * 2 + e.id) * dt * 1.1;
    }
    if (e.type === "fang") {
      if (e.wind > 0) {
        e.wind -= dt;
        speed = 0;
        if (e.wind <= 0) {
          e.dash = 0.42;
        }
      } else if (e.dash > 0) {
        e.x += e.dx * dt * 13;
        e.z += e.dz * dt * 13;
        e.dash -= dt;
        speed = 0;
      } else if (e.clock <= 0 && d < 11) {
        e.wind = 0.7;
        e.dx = ux;
        e.dz = uz;
        e.clock = 4.5;
      }
    }
    if (e.type === "boss") {
      speed = d < 7 ? 0 : speed;
      if (e.clock <= 0) {
        s.zones.push({
          x: s.player.x,
          z: s.player.z,
          r: 5,
          wind: 1.6,
          life: 0.5,
          power: 25,
        });
        for (let i = 0; i < 10; i++) {
          const a = Math.atan2(uz, ux) + (i - 4.5) * 0.19;
          s.shots.push({
            x: e.x,
            z: e.z,
            dx: Math.cos(a),
            dz: Math.sin(a),
            life: 7,
            power: 14,
          });
        }
        e.clock = e.hp < e.maxHp * 0.5 ? 2.3 : 3.5;
      }
    }
    e.x += ux * speed * dt;
    e.z += uz * speed * dt;
    if (d < (e.type === "boss" ? 2 : 0.72)) hurt(s, t.damage);
  }
}
export function update(s, dt = DT) {
  if (s.phase !== "playing" || s.paused) return;
  s.tick++;
  s.time += dt;
  s.invuln = Math.max(0, s.invuln - dt);
  s.charge = Math.min(1, s.charge + dt / s.config.chargeSeconds);
  let dx = s.keys.x,
    dz = s.keys.z;
  if (s.target) {
    const d = distance(s.player, s.target);
    if (d < 0.16) s.target = null;
    else {
      dx = (s.target.x - s.player.x) / d;
      dz = (s.target.z - s.player.z) / d;
    }
  }
  const mag = Math.hypot(dx, dz);
  if (mag) {
    s.player.x += (dx / mag) * 7 * dt;
    s.player.z += (dz / mag) * 7 * dt;
    const d = Math.hypot(s.player.x, s.player.z);
    if (d > 19) {
      s.player.x *= 19 / d;
      s.player.z *= 19 / d;
    }
  }
  const wave = Math.min(12, Math.floor(s.time / s.config.waveSeconds) + 1);
  if (wave !== s.wave) {
    s.wave = wave;
    s.hp = Math.min(s.maxHp, s.hp + 7);
    event(s, "wave", `Wave ${wave}: ${WAVES[wave - 1][0]}`);
    if (wave === 5 || wave === 10) s.waveNotice = wave;
  }
  if (s.wave === 12 && !s.bossSpawned) {
    spawnEnemy(s, "boss");
    s.bossSpawned = true;
    event(s, "boss", "The Bellkeeper has arrived.");
  }
  s.spawnClock -= dt;
  const row = WAVES[s.wave - 1];
  while (s.spawnClock <= 0) {
    s.spawnClock += 1 / (s.wave === 9 ? s.config.lateWaveRate : row[2]);
    if (s.enemies.length < s.config.enemyCap)
      spawnEnemy(s, row[1][Math.floor(rand(s) * row[1].length)]);
  }
  s.bolt -= dt;
  if (s.bolt <= 0) {
    const nearest = s.enemies
      .filter((e) => e.hp > 0 && distance(e, s.player) < 10)
      .sort((a, b) => distance(a, s.player) - distance(b, s.player))[0];
    if (nearest) {
      damage(s, nearest, 8, "keeper");
      s.effects.push({
        kind: "beam",
        x: s.player.x,
        z: s.player.z,
        tx: nearest.x,
        tz: nearest.z,
        color: 0xf9e4b4,
        life: 0.14,
        max: 0.14,
        r: 1,
      });
    }
    s.bolt = 0.48;
  }
  for (const a of s.squad) {
    a.clock -= dt;
    if (a.clock <= 0) {
      const firstEffect = s.effects.length;
      allyAttack(s, a);
      // Presentation metadata only: preserve authoritative damage centers and ticks.
      for (let i = firstEffect; i < s.effects.length; i++) {
        s.effects[i].sourceId = a.id;
        s.effects[i].sourceType = a.type;
      }
      a.clock = TYPES[a.type].rate;
    }
  }
  attackEnemies(s, dt);
  for (const z of s.zones) {
    if (z.wind > 0) z.wind -= dt;
    else {
      z.life -= dt;
      if (distance(s.player, z) < z.r) hurt(s, z.power);
    }
  }
  s.zones = s.zones.filter((z) => z.life > 0);
  for (const b of s.shots) {
    b.x += b.dx * 6 * dt;
    b.z += b.dz * 6 * dt;
    b.life -= dt;
    if (distance(b, s.player) < 0.55) {
      hurt(s, b.power);
      b.life = 0;
    }
  }
  s.shots = s.shots.filter((b) => b.life > 0);
  for (const f of s.effects) f.life -= dt;
  s.effects = s.effects.filter((f) => f.life > 0).slice(-140);
  s.enemies = s.enemies.filter((e) => e.hp > 0);
  if (s.hp <= 0) {
    s.phase = "lost";
    releaseAll(s);
    event(s, "outcome", "The lantern goes dark.");
  } else if (s.bossDefeated) {
    s.phase = "won";
    releaseAll(s);
    event(s, "outcome", "You carried the night into dawn.");
  }
}
export function snapshot(s) {
  return {
    version: s.version,
    seed: s.seed,
    scenario: s.scenario,
    tick: s.tick,
    time: +s.time.toFixed(3),
    wave: s.wave,
    phase: s.phase,
    paused: s.paused,
    mode: s.mode,
    hp: +s.hp.toFixed(2),
    charge: +s.charge.toFixed(3),
    player: { ...s.player },
    target: s.target ? { ...s.target } : null,
    keys: { ...s.keys },
    squad: s.squad.map((a) => ({ id: a.id, type: a.type })),
    hostiles: s.enemies.length,
    nearby: s.enemies.filter((e) => distance(e, s.player) < 6).length,
    enemies: s.enemies.map((e) => ({
      id: e.id,
      type: e.type,
      x: +e.x.toFixed(2),
      z: +e.z.toFixed(2),
      hp: +e.hp.toFixed(1),
      wind: e.wind,
    })),
    available: availableRecipes(s).map((r) => r.result),
    candidates: candidates(s),
    boss: s.enemies.find((e) => e.type === "boss")?.hp ?? null,
    kills: s.kills,
    stats: structuredClone(s.stats),
    events: s.events.slice(-15),
  };
}
