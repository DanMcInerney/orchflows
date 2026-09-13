// Presentation-only guidance for the approved twelve-wave content arc.
// Spawn composition, cadence and combat remain in content.js/simulation.js.
export const ENCOUNTER_GUIDE = [
  {
    stage: "learn",
    focus:
      "Your lantern fires automatically. Bind an Emberling to burn groups.",
  },
  {
    stage: "learn",
    focus:
      "Thornbacks protect. Voltwings catch spread-out foes. Choose your first pair.",
  },
  {
    stage: "test",
    focus:
      "Leave fresh ground ahead. Mire poison punishes retracing your path.",
  },
  {
    stage: "test",
    focus: "Hold your ingredients. The first awakening opens at wave 5.",
  },
  {
    stage: "release",
    focus:
      "Awaken a pair in the Field guide. New space means time to rebuild your circle.",
  },
  {
    stage: "combine",
    focus:
      "Chargers and poison work together. Fang hunts heavy targets; Moth restores vitality.",
  },
  {
    stage: "combine",
    focus:
      "Protect now or keep your next recipe? An evolution consumes its ingredients.",
  },
  {
    stage: "combine",
    focus:
      "Check your ascension companions. Intercept wanted foes before your circle defeats them.",
  },
  {
    stage: "mastery",
    focus:
      "The horde is closing in. Move through fresh ground until the tenth bell.",
  },
  {
    stage: "release",
    focus:
      "Ascend in the Field guide. Your earned power can open the whole arena.",
  },
  {
    stage: "recovery",
    focus:
      "Use the breathing room. The Bellkeeper comes with the twelfth bell.",
  },
  {
    stage: "mastery",
    focus:
      "Watch the Bellkeeper. Leave its large warning circle; move across the volley.",
  },
];

export function waveGuidance(state) {
  if (state.wave === 11 && !state.stats.evolutions.some((e) => e.wave >= 10))
    return "One bell remains. Check your ascension ingredients before the Bellkeeper arrives.";
  return ENCOUNTER_GUIDE[state.wave - 1].focus;
}
