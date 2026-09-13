import { createScenario as createGame } from "../src/scenarios.js";
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  act,
  update,
  spawnEnemy,
  availableRecipes,
  snapshot,
  DT,
  releaseAll,
} from "../src/simulation.js";
function ticks(s, n) {
  for (let i = 0; i < n; i++) update(s, DT);
}
test("ally effects identify their visual source without changing the combat center", () => {
  const s = createGame(1, "pre-evolution", { route: "storm" });
  ticks(s, 1);
  const source = s.squad.find((a) => a.type === "volt");
  const beams = s.effects.filter(
    (e) => e.kind === "beam" && e.sourceId === source.id,
  );
  assert.ok(beams.length > 0);
  assert.ok(
    beams.every(
      (e) =>
        e.sourceType === "volt" && e.x === s.player.x && e.z === s.player.z,
    ),
  );
  assert.ok(s.stats.damageBy.volt > 0);
});
test("Moth healing cannot revive a creature or boss killed earlier in the same tick", () => {
  for (const type of ["ember", "boss"]) {
    const s = createGame();
    act(s, { type: "start" });
    s.spawnClock = 100;
    s.bossSpawned = type === "boss";
    const victim = spawnEnemy(s, type, 3);
    Object.assign(victim, { x: 3, z: 0, hp: 1 });
    const healer = spawnEnemy(s, "moth", 3);
    Object.assign(healer, { x: 3, z: 0, clock: 0, hp: 10 });
    ticks(s, 1);
    assert.equal(s.kills, 1);
    assert.equal(
      s.enemies.some((e) => e.id === victim.id),
      false,
    );
    assert.equal(healer.hp, 18, "living creatures still receive healing");
    assert.equal(s.phase, type === "boss" ? "won" : "playing");
  }
});
test("capture consumes one real nearby enemy and cannot bypass charge", () => {
  const s = createGame();
  act(s, { type: "start" });
  const e = spawnEnemy(s, "ember", 3);
  const before = s.enemies.length;
  assert.equal(act(s, { type: "capture", id: e.id }), true);
  assert.equal(s.enemies.length, before - 1);
  assert.equal(s.squad[0].type, "ember");
  assert.equal(s.charge, 0);
  const e2 = spawnEnemy(s, "thorn", 3);
  assert.equal(act(s, { type: "capture", id: e2.id }), false);
  assert.equal(s.squad.length, 1);
});
test("paused time never charges or moves; release clears keyboard and target", () => {
  const s = createGame();
  act(s, { type: "start" });
  s.charge = 0;
  act(s, { type: "move", x: 15, z: 0 });
  act(s, { type: "pause" });
  ticks(s, 120);
  assert.equal(s.tick, 0);
  assert.equal(s.charge, 0);
  assert.equal(s.player.x, 0);
  assert.equal(s.target, null);
});
test("evolution needs legal ingredients and wave gate; consumes them and grants a new role", () => {
  const s = createGame(7, "pre-evolution");
  s.wave = 4;
  assert.equal(availableRecipes(s).length, 0);
  assert.equal(act(s, { type: "evolve", result: "pyre" }), false);
  s.wave = 5;
  assert.equal(act(s, { type: "evolve", result: "pyre" }), true);
  assert.deepEqual(
    s.squad.map((a) => a.type),
    ["pyre"],
  );
  assert.equal(s.stats.evolutions[0].wave, 5);
  assert.equal(act(s, { type: "evolve", result: "solar" }), false);
});
test("second ascension consumes evolved and two distinct base companions", () => {
  const s = createGame(7, "second-evolution");
  assert.equal(act(s, { type: "evolve", result: "solar" }), true);
  assert.deepEqual(
    s.squad.map((a) => a.type),
    ["solar"],
  );
});
test("every alternate recipe changes real combat and its ascension consumes the planned ingredients", () => {
  for (const [route, result] of [
    ["pyre", "solar"],
    ["storm", "world"],
    ["dusk", "eclipse"],
  ]) {
    const first = createGame(91, "pre-evolution", { route });
    assert.equal(act(first, { type: "evolve", result: route }), true);
    ticks(first, 180);
    assert.ok(first.kills > 0);
    assert.ok(first.stats.damageBy[route] > 0);
    const second = createGame(91, "second-evolution", { route });
    assert.equal(act(second, { type: "evolve", result }), true);
    ticks(second, 180);
    assert.ok(second.kills > 0);
    assert.ok(second.stats.damageBy[result] > 0);
  }
});
test("seed reset reproduces mixed behavior and bounded actions", () => {
  const run = () => {
    const s = createGame(101, "roles");
    act(s, { type: "move", x: 12, z: 6 });
    ticks(s, 180);
    return snapshot(s);
  };
  assert.deepEqual(run(), run());
});
test("diagonal movement is normalized and arena border keeps player in bounds", () => {
  const a = createGame(),
    b = createGame();
  act(a, { type: "start" });
  act(b, { type: "start" });
  act(a, { type: "keys", x: 1, z: 0 });
  act(b, { type: "keys", x: 1, z: 1 });
  ticks(a, 60);
  ticks(b, 60);
  assert.ok(Math.abs(Math.hypot(b.player.x, b.player.z) - a.player.x) < 1e-8);
  ticks(a, 600);
  assert.ok(Math.hypot(a.player.x, a.player.z) <= 19.000001);
  releaseAll(a);
  assert.deepEqual(a.keys, { x: 0, z: 0 });
});
test("boss defeat is decided by damage, death has its own outcome, restart is fresh", () => {
  const s = createGame(7, "boss");
  ticks(s, 1);
  assert.ok(s.enemies.some((e) => e.type === "boss"));
  s.enemies.find((e) => e.type === "boss").hp = 0.1;
  s.enemies.find((e) => e.type === "boss").x = 3;
  s.enemies.find((e) => e.type === "boss").z = 0;
  ticks(s, 120);
  assert.equal(s.phase, "won");
  const failed = createGame(7, "boss-danger");
  failed.hp = 0.1;
  failed.squad = [];
  failed.bolt = 5;
  spawnEnemy(failed, "thorn", 0);
  ticks(failed, 1);
  assert.equal(failed.phase, "lost");
  const fresh = createGame();
  assert.equal(fresh.phase, "title");
  assert.equal(fresh.enemies.length, 0);
  assert.equal(fresh.squad.length, 0);
  assert.equal(fresh.charge, 1);
});
