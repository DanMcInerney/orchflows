import "./asset-preview.css";
import * as THREE from "three";
import {
  loadManifest,
  loadAsset,
  cloneAsset,
  createAssetBatch,
  disposeAsset,
} from "./assets.js";
import {
  createRenderer,
  createLitScene,
  createGameCamera,
  fitGameCamera,
  graphicsBackend,
} from "./render-settings.js";

const $ = (id) => document.getElementById(id),
  renderer = createRenderer($("preview-world"), {
    dpr: 1,
    label: "Actual Nightbind GLB preview",
  }),
  scene = createLitScene(),
  camera = createGameCamera();
let manifest = null,
  selected = null,
  cache = new Map(),
  objects = new THREE.Group(),
  markers = new THREE.Group(),
  batches = [],
  request = 0,
  abort = null,
  report = { status: "loading" },
  motion = false;
scene.add(objects, markers);
const ground = new THREE.Mesh(
  new THREE.CylinderGeometry(20.2, 20.2, 0.1, 80),
  new THREE.MeshStandardMaterial({ color: 0x243c3e, roughness: 1 }),
);
ground.position.y = -0.08;
scene.add(ground);
const references = new THREE.Group();
scene.add(references);
const grid = new THREE.GridHelper(40, 40, 0x536e69, 0x29464a);
grid.position.y = -0.015;
references.add(grid);
const axes = new THREE.AxesHelper(3);
references.add(axes);
for (const [x, z, r, c] of [
  [-4, 2, 2.3, 0x9c78d0],
  [5, -3, 5, 0xe0b79c],
]) {
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(r * 0.85, r, 48),
    new THREE.MeshBasicMaterial({
      color: c,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.set(x, 0.035, z);
  references.add(ring);
}
const reference = new THREE.Mesh(
  new THREE.CapsuleGeometry(0.42, 0.9, 3, 8),
  new THREE.MeshBasicMaterial({ color: 0xd9d3b8, wireframe: true }),
);
reference.position.set(-3, 0.88, 0);
references.add(reference);
const p = new THREE.Vector3(),
  q = new THREE.Quaternion(),
  scale = new THREE.Vector3(1, 1, 1),
  axis = new THREE.Vector3(0, 1, 0);

function clearObjects() {
  for (const batch of batches) batch.dispose();
  batches = [];
  objects.clear();
  markers.traverse((node) => {
    node.geometry?.dispose();
    if (node.material)
      for (const material of Array.isArray(node.material)
        ? node.material
        : [node.material])
        material.dispose();
  });
  markers.clear();
}
function error(message) {
  $("preview-error").textContent = message;
  $("preview-status").textContent = "Asset inspection blocked";
  report = { ...report, status: "error", error: message };
  observe();
}
function observe() {
  const value = {
    version: 1,
    kind: "asset inspection",
    status: "ready",
    ...report,
    mode: $("preview-mode").value,
    facing: Number($("preview-facing").value),
    viewport: {
      width: innerWidth,
      height: innerHeight,
      dpr: renderer.getPixelRatio(),
    },
    camera: { position: camera.position.toArray(), halfHeight: camera.top },
    backend: graphicsBackend(renderer),
    renderer: { ...renderer.info.render },
    resources: { ...renderer.info.memory },
    motion,
  };
  $("asset-observation").textContent = JSON.stringify(value);
  $("asset-diagnostics").textContent = JSON.stringify(value, null, 2);
}
async function ensure(id) {
  if (cache.has(id)) return cache.get(id);
  const entry = manifest.assets.find((a) => a.id === id);
  if (!entry) throw Error(`Manifest does not contain required asset: ${id}`);
  const asset = await loadAsset(entry, { signal: abort.signal });
  cache.set(id, asset);
  return asset;
}
function cameraFor(mode, bounds) {
  const target = new THREE.Vector3();
  let halfHeight = 18;
  if (
    ["detail", "portrait", "kit"].includes(mode) &&
    bounds &&
    !bounds.isEmpty()
  ) {
    bounds.getCenter(target);
    const size = bounds.getSize(new THREE.Vector3());
    halfHeight = Math.max(
      0.9,
      Math.max(size.y, size.z * 0.8, size.x * 0.75) * 0.8,
    );
  }
  fitGameCamera(camera, innerWidth, innerHeight, {
    halfHeight,
    target,
    portrait: mode === "portrait",
  });
}
function makeSockets(asset, object) {
  object.updateMatrixWorld(true);
  for (const socket of asset.diagnostics.sockets) {
    const node = object.getObjectByName(socket.name);
    if (!node) continue;
    const marker = new THREE.AxesHelper(0.45);
    marker.matrixAutoUpdate = false;
    marker.matrix.copy(node.matrixWorld);
    markers.add(marker);
  }
  markers.visible = $("preview-sockets").checked;
}
function pose(name, time) {
  if (name.includes("wing_l"))
    return { axis: "z", angle: Math.sin(time * 5) * 0.3 };
  if (name.includes("wing_r"))
    return { axis: "z", angle: -Math.sin(time * 5) * 0.3 };
  if (name.includes("jaw"))
    return { axis: "x", angle: (Math.sin(time * 3) + 1) * 0.08 };
}

async function display() {
  if (!manifest || !$("asset-select").value) return;
  const current = ++request;
  clearObjects();
  $("preview-error").textContent = "";
  $("preview-status").textContent = "Loading actual GLB…";
  report = { status: "loading" };
  observe();
  try {
    const mode = $("preview-mode").value,
      asset = await ensure($("asset-select").value);
    if (current !== request) return;
    selected = asset;
    const yaw = (Number($("preview-facing").value) * Math.PI) / 180;
    q.setFromAxisAngle(axis, yaw);
    scale.setScalar(1);
    if (mode === "busy" || mode === "mixed") {
      const available =
        mode === "mixed"
          ? manifest.assets
              .filter((e) =>
                ["ember", "thorn", "volt", "mire", "fang", "moth"].includes(
                  e.id,
                ),
              )
              .map((e) => e.id)
          : [asset.id];
      if (!available.length)
        throw Error(
          "No base creature exports are available for mixed inspection.",
        );
      const loaded = await Promise.all(available.map(ensure));
      if (current !== request) return;
      for (const [i, a] of loaded.entries()) {
        const count =
            Math.floor(180 / loaded.length) + (i < 180 % loaded.length ? 1 : 0),
          batch = createAssetBatch(a, count);
        batch.items = [];
        for (let j = 0; j < count; j++) {
          const n = j * loaded.length + i,
            angle = n * 2.399963,
            r = 3 + ((n * 17) % 145) / 10;
          p.set(Math.cos(angle) * r, 0, Math.sin(angle) * r);
          batch.set(j, p, q, scale);
          batch.items.push({
            position: p.clone(),
            quaternion: q.clone(),
            scale: scale.clone(),
          });
        }
        batch.commit(count);
        objects.add(batch.group);
        batches.push(batch);
      }
    } else {
      const object = cloneAsset(asset);
      object.quaternion.copy(q);
      if (asset.id === "hanging_bell") {
        object.position.y = -asset.diagnostics.bounds.min[1] + 0.2;
        report.previewPlacement = {
          reason: "Suspended asset raised above reference floor; authored top pivot preserved.",
          translation: object.position.toArray(),
        };
      }
      objects.add(object);
      makeSockets(asset, object);
      if (
        asset.id === "keeper" &&
        manifest.assets.some((e) => e.id === "lantern")
      ) {
        const lantern = cloneAsset(await ensure("lantern"));
        if (current !== request) return;
        const socket = object.getObjectByName("socket_lantern");
        if (socket) socket.add(lantern);
        else
          report.attachmentWarning =
            "Keeper has no socket_lantern; separate lantern was not attached.";
      }
      if (
        asset.id === "bell_arch" &&
        manifest.assets.some((e) => e.id === "hanging_bell")
      ) {
        const bell = cloneAsset(await ensure("hanging_bell"));
        if (current !== request) return;
        const socket = object.getObjectByName("socket_bell");
        if (socket) {
          socket.add(bell);
          report.attachment = { id: "hanging_bell", socket: "socket_bell" };
        } else
          report.attachmentWarning =
            "Arch has no socket_bell; suspended bell was not attached.";
      }
      if (mode === "kit") {
        const second = cloneAsset(asset);
        second.rotation.y = yaw + Math.PI / 12;
        second.position.y = object.position.y;
        if (asset.id !== "rim_segment")
          second.position.x = asset.diagnostics.bounds.size[0];
        objects.add(second);
      }
    }
    const bounds = new THREE.Box3().setFromObject(objects);
    cameraFor(mode, bounds);
    references.visible = $("preview-warnings").checked;
    ground.visible = asset.id !== "arena_floor";
    report = {
      ...report,
      status: "ready",
      asset: asset.diagnostics,
      manifestVersion: manifest.schemaVersion,
      instances:
        mode === "busy" || mode === "mixed" ? 180 : mode === "kit" ? 2 : 1,
      loadedIds: [...cache.keys()],
      boundsIncludingAssembly: {
        min: bounds.min.toArray(),
        max: bounds.max.toArray(),
      },
    };
    $("preview-status").textContent = `Loaded ${asset.id} · actual GLB`;
    $("asset-summary").textContent =
      `${asset.diagnostics.triangles.toLocaleString()} triangles · ${asset.diagnostics.meshes.length} mesh primitives · ${asset.diagnostics.materials.length} materials · ${(asset.diagnostics.bytes / 1024).toFixed(1)} KiB. Bounds ${asset.diagnostics.bounds.size.map((n) => n.toFixed(2)).join(" × ")}.`;
    $("preview-caption").textContent =
      `${mode === "game" ? "Game camera: 20 horizontal px/unit at 720px height" : "Inspection view: " + mode} · DPR 1 · ${asset.entry.file} · ${asset.diagnostics.animations.length} exported clips`;
    renderer.render(scene, camera);
    observe();
  } catch (e) {
    if (current === request && e.name !== "AbortError") error(e.message);
  }
}

async function reload() {
  ++request;
  abort?.abort();
  abort = new AbortController();
  clearObjects();
  for (const asset of cache.values()) disposeAsset(asset);
  cache.clear();
  manifest = null;
  selected = null;
  report = { status: "loading" };
  $("preview-error").textContent = "";
  $("preview-status").textContent = "Loading manifest…";
  try {
    manifest = await loadManifest({ signal: abort.signal });
    const previous = $("asset-select").value;
    $("asset-select").replaceChildren(
      ...manifest.assets.map((entry) => new Option(entry.id, entry.id)),
    );
    if (manifest.assets.some((a) => a.id === previous))
      $("asset-select").value = previous;
    if (!manifest.assets.length) {
      error(
        "The manifest has no exported assets yet. Add the representative keeper/lantern and arch/rim entries, then Reload assets.",
      );
      return;
    }
    await display();
  } catch (e) {
    if (e.name !== "AbortError") error(e.message);
  }
}
for (const id of ["asset-select", "preview-mode", "preview-facing"])
  $(id).onchange = display;
$("reload-assets").onclick = reload;
$("preview-warnings").onchange = () => {
  references.visible = $("preview-warnings").checked;
};
$("preview-sockets").onchange = () => {
  markers.visible = $("preview-sockets").checked;
};
$("preview-motion").onchange = () => {
  motion = $("preview-motion").checked;
};
$("toggle-panel").onclick = () => {
  $("preview-panel").classList.toggle("hidden");
  $("toggle-panel").textContent = $("preview-panel").classList.contains(
    "hidden",
  )
    ? "Show controls"
    : "Hide controls";
};
let frames = 0;
renderer.setAnimationLoop((now) => {
  if (motion) {
    for (const batch of batches) {
      batch.items.forEach((item, i) =>
        batch.set(i, item.position, item.quaternion, item.scale, (name) =>
          pose(name, now / 1000 + i * 0.3),
        ),
      );
      batch.commit(batch.items.length);
    }
    if (!batches.length)
      objects.traverse((node) => {
        const action = pose(node.name, now / 1000);
        if (!action) return;
        if (!node.userData.previewNeutral)
          node.userData.previewNeutral = node.quaternion.clone();
        node.quaternion
          .copy(node.userData.previewNeutral)
          .multiply(
            new THREE.Quaternion().setFromAxisAngle(
              new THREE.Vector3(
                action.axis === "x" ? 1 : 0,
                0,
                action.axis === "z" ? 1 : 0,
              ),
              action.angle,
            ),
          );
      });
  }
  renderer.render(scene, camera);
  if (frames++ % 30 === 0) observe();
});
function resize() {
  renderer.setSize(innerWidth, innerHeight);
  cameraFor($("preview-mode").value, new THREE.Box3().setFromObject(objects));
}
addEventListener("resize", resize);
addEventListener("pagehide", () => {
  abort?.abort();
  renderer.setAnimationLoop(null);
  clearObjects();
  for (const a of cache.values()) disposeAsset(a);
  renderer.dispose();
});
resize();
reload();
