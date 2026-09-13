import { TYPES } from "./content.js";
import { loadManifest, loadAsset, disposeAsset } from "./assets.js";

export const MODEL_IDS = [
  ...Object.keys(TYPES), "keeper", "lantern", "arena_floor", "rim_segment",
  "bell_arch", "hanging_bell", "shrine_plinth", "votive", "rubble_cluster",
];

export async function loadGameAssets(onProgress = () => {}) {
  const manifest = await loadManifest();
  const entries = new Map(manifest.assets.map((entry) => [entry.id, entry]));
  for (const id of MODEL_IDS)
    if (!entries.has(id)) throw Error(`Required model is missing: ${id}`);
  const library = new Map();
  let complete = 0;
  const loaded = await Promise.allSettled(MODEL_IDS.map(async (id) => {
    const asset = await loadAsset(entries.get(id));
    library.set(id, asset);
    if (asset.diagnostics.warnings.length)
      throw Error(`${id}: ${asset.diagnostics.warnings.join(" ")}`);
    if ([...Object.keys(TYPES), "keeper", "lantern"].includes(id)) {
      const portrait = asset.entry.portrait;
      if (!portrait?.startsWith("/models/portraits/"))
        throw Error(`${id}: required portrait is missing from manifest.`);
      const image = new Image();
      image.src = portrait;
      try { await image.decode(); }
      catch { throw Error(`${id}: portrait could not be loaded.`); }
    }
    onProgress(++complete, MODEL_IDS.length, id);
  }));
  const failed = loaded.find((result) => result.status === "rejected");
  if (failed) {
    for (const asset of library.values()) disposeAsset(asset);
    throw failed.reason;
  }
  return { library, manifest };
}
