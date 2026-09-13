// Original synthesized glass, bell and low drum cues. No external media dependency.
export function createAudio(settings) {
  let context, master, ambience, stateRef, lastTick = -1, voices = 0, played = 0;
  const seen = new WeakSet();
  let error = null, lastAttack = -1;
  function apply() {
    if (master) master.gain.setTargetAtTime(settings.muted ? 0 : settings.volume * 0.48, context.currentTime, 0.04);
  }
  async function unlock() {
    try {
      if (!context) {
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (!Audio) throw Error("Web Audio is unavailable; visual cues remain active.");
        context = new Audio();
        master = context.createGain();
        master.connect(context.destination);
        ambience = context.createGain();
        ambience.gain.value = 0;
        ambience.connect(master);
        for (const frequency of [73.42, 110]) {
          const oscillator = context.createOscillator();
          oscillator.type = "sine";
          oscillator.frequency.value = frequency;
          oscillator.connect(ambience);
          oscillator.start();
        }
        apply();
      }
      if (context.state === "suspended") await context.resume();
    } catch (e) { error = e.message; }
  }
  function tone(frequency, duration, gain, type = "sine", delay = 0, end = frequency) {
    if (!context || context.state !== "running" || voices >= 18 || settings.muted) return;
    const start = context.currentTime + delay, oscillator = context.createOscillator(), envelope = context.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, start);
    oscillator.frequency.exponentialRampToValueAtTime(Math.max(20, end), start + duration);
    envelope.gain.setValueAtTime(0.0001, start);
    envelope.gain.exponentialRampToValueAtTime(gain, start + 0.012);
    envelope.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    oscillator.connect(envelope); envelope.connect(master);
    voices++; played++;
    oscillator.onended = () => { oscillator.disconnect(); envelope.disconnect(); voices--; };
    oscillator.start(start); oscillator.stop(start + duration + 0.025);
  }
  function update(s) {
    if (!context) return;
    apply();
    ambience.gain.setTargetAtTime(s.phase === "playing" && !s.paused ? 0.013 : 0, context.currentTime, 0.2);
    if (stateRef !== s) { stateRef = s; lastTick = -1; lastAttack = -1; }
    if (lastTick === s.tick || s.paused) return;
    lastTick = s.tick;
    for (const event of s.events) {
      if (seen.has(event)) continue;
      seen.add(event);
      if (event.type === "capture") [392, 523.25, 783.99].forEach((f, i) => tone(f, 0.45, 0.1, "sine", i * 0.09));
      if (event.type === "evolve") [130.81, 261.63, 392, 523.25, 783.99].forEach((f, i) => tone(f, 1.45, 0.12, "sine", i * 0.07));
      if (event.type === "damage") tone(90, 0.19, 0.11, "triangle", 0, 38);
      if (event.type === "wave") tone(220, 0.65, 0.08, "sine", 0, 219);
      if (event.type === "boss") [82.41, 123.47].forEach((f, i) => tone(f, 1.4, 0.12, "triangle", i * 0.25));
      if (event.type === "outcome") [196, s.phase === "won" ? 293.66 : 146.83, s.phase === "won" ? 392 : 98].forEach((f, i) => tone(f, 1.5, 0.13, "sine", i * 0.2));
    }
    if (s.phase === "playing" && s.time - lastAttack > 0.18) {
      const effect = s.effects.find((f) => f.kind === "beam" && !seen.has(f));
      if (effect) {
        seen.add(effect); lastAttack = s.time;
        tone(effect.sourceType ? 340 : 660, 0.08, 0.026, "sine", 0, 180);
      }
    }
  }
  return { unlock, update, apply, describe: () => ({ available: !!context, state: context?.state || "waiting for gesture", muted: settings.muted, volume: settings.volume, voices, cuesPlayed: played, error }), dispose: () => context?.close() };
}
