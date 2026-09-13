const defaults = {
  muted: false,
  volume: 0.4,
  reducedMotion: matchMedia("(prefers-reduced-motion: reduce)").matches,
};
let stored = {};
try { stored = JSON.parse(localStorage.getItem("nightbind-settings-v1") || "{}"); }
catch { /* Preferences are optional; blocked storage must not prevent play. */ }
export const settings = {
  muted: typeof stored.muted === "boolean" ? stored.muted : defaults.muted,
  volume: Number.isFinite(stored.volume) ? Math.max(0, Math.min(1, stored.volume)) : defaults.volume,
  reducedMotion: typeof stored.reducedMotion === "boolean" ? stored.reducedMotion : defaults.reducedMotion,
};
export function saveSettings() {
  document.documentElement.classList.toggle("reduced-motion", settings.reducedMotion);
  try { localStorage.setItem("nightbind-settings-v1", JSON.stringify(settings)); }
  catch { /* Gameplay does not depend on persistent preferences. */ }
}
saveSettings();
