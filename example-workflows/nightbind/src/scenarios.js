import { BASE } from "./content.js";
import { createGame, spawnEnemy, rand } from "./simulation.js";

export const SCENARIOS = [
  "fresh",
  "pre-evolution",
  "wrong-recipe",
  "late-pressure",
  "second-evolution",
  "roles",
  "boss",
  "boss-danger",
];

// Included only by the explicit diagnostic build; ordinary release has no fixtures.
export function createScenario(seed = 12345, scenario = "fresh", config = {}) {
  if (!SCENARIOS.includes(scenario)) throw Error("Unknown scenario");
  const s = createGame(seed, config);
  s.scenario = scenario;
  if (scenario !== "fresh") {
    s.phase = "playing";
    s.wave =
      scenario === "late-pressure"
        ? 9
        : scenario === "second-evolution"
          ? 10
          : scenario.startsWith("boss")
            ? 12
            : scenario === "roles"
              ? 7
              : scenario === "wrong-recipe"
                ? 4
                : 5;
    s.time =
      (s.wave - 1) * s.config.waveSeconds +
      (scenario === "wrong-recipe" ? 12 : 0);
    s.charge = scenario === "wrong-recipe" ? 0.15 : 1;
    const route = config.route || "pyre";
    const pairs = {
      pyre: ["ember", "thorn"],
      storm: ["volt", "mire"],
      dusk: ["fang", "moth"],
    };
    const ascensions = {
      pyre: ["pyre", "volt", "moth"],
      storm: ["storm", "thorn", "fang"],
      dusk: ["dusk", "ember", "mire"],
    };
    const roster =
      scenario === "late-pressure"
        ? ["volt", "mire", "moth", "pyre", "fang", "moth"]
        : scenario === "second-evolution"
          ? ascensions[route]
          : scenario.startsWith("boss")
            ? ["solar", "storm", "fang"]
            : scenario === "wrong-recipe"
              ? ["ember", "mire", "moth"]
              : pairs[route];
    roster.forEach((type) => s.squad.push({ id: s.nextId++, type, clock: 0 }));
    if (scenario === "boss-danger") s.hp = 18;
    for (
      let i = 0;
      i < (scenario === "roles" || scenario === "late-pressure" ? 60 : 85);
      i++
    )
      spawnEnemy(s, BASE[i % 6], 6 + rand(s) * 12);
  }
  return s;
}
