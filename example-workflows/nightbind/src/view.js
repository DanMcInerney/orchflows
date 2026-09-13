import * as THREE from "three";
import { TYPES } from "./content.js";
import { cloneAsset, createAssetBatch, disposeAsset } from "./assets.js";
import { loadGameAssets } from "./game-assets.js";
import { createRenderer, createLitScene, createGameCamera, fitGameCamera } from "./render-settings.js";

export async function createView(container, { onProgress, settings }) {
  const renderer = createRenderer(container, { label: "Nightbind arena. Click the ground to move." });
  let loaded;
  try { loaded = await loadGameAssets(onProgress); }
  catch (error) { renderer.dispose(); renderer.domElement.remove(); throw error; }
  const { library, manifest } = loaded;
  const scene = createLitScene(), camera = createGameCamera();
  const owned = [], environmentBatches = [];
  const object = (id, x = 0, y = 0, z = 0, yaw = 0) => {
    const model = cloneAsset(library.get(id));
    model.position.set(x, y, z); model.rotation.y = yaw; scene.add(model); return model;
  };
  object("arena_floor");
  const arch = object("bell_arch", 18.5, 0, -12, Math.atan2(-18.5, 12));
  const bell = cloneAsset(library.get("hanging_bell"));
  arch.getObjectByName("socket_bell").add(bell);
  object("shrine_plinth", -22, 0, 0, Math.PI / 2);
  const p = new THREE.Vector3(), q = new THREE.Quaternion(), scale = new THREE.Vector3(1, 1, 1), up = new THREE.Vector3(0, 1, 0);
  for (const [id, placements] of [
    ["rim_segment", Array.from({ length: 24 }, (_, i) => [0, 0, 0, i * Math.PI / 12])],
    ["votive", [[22, 0, 2, -Math.PI / 2], [22.6, 0, 3.7, -Math.PI / 2], [21.6, 0, 5.4, -Math.PI / 2]]],
    ["rubble_cluster", [[-19.5, 0, -11, 0.4], [12, 0, 18.7, 2.4]]],
  ]) {
    const batch = createAssetBatch(library.get(id), placements.length);
    placements.forEach(([x, y, z, yaw], i) => batch.set(i, p.set(x, y, z), q.setFromAxisAngle(up, yaw), scale));
    batch.commit(placements.length); scene.add(batch.group); environmentBatches.push(batch);
  }
  const player = object("keeper"), lantern = cloneAsset(library.get("lantern"));
  player.getObjectByName("socket_lantern").add(lantern);
  const arm = player.getObjectByName("arm_r"), armNeutral = arm.quaternion.clone();
  const captureSocket = player.getObjectByName("socket_capture");
  const lanternLight = new THREE.PointLight(0xffcb77, 1.2, 5, 2);
  captureSocket.add(lanternLight);
  const lightOrigin = new THREE.Vector3();

  function mesh(geometry, material, capacity = 0) {
    const result = capacity ? new THREE.InstancedMesh(geometry, material, capacity) : new THREE.Mesh(geometry, material);
    if (capacity) { result.count = 0; result.frustumCulled = false; result.instanceMatrix.setUsage(THREE.DynamicDrawUsage); }
    scene.add(result); owned.push(result); return result;
  }
  const circleGeo = new THREE.TorusGeometry(0.66, 0.035, 3, 28);
  const halo = mesh(circleGeo, new THREE.MeshBasicMaterial({ color: 0xf7dca7 }));
  halo.rotation.x = Math.PI / 2;
  const allyRings = mesh(circleGeo, new THREE.MeshBasicMaterial({ color: 0xb9f4de }), 6);
  const shadows = mesh(new THREE.CircleGeometry(0.55, 12), new THREE.MeshBasicMaterial({ color: 0x071b20, transparent: true, opacity: 0.35, depthWrite: false }), 250);
  shadows.rotation.x = 0;
  const fxRings = mesh(new THREE.TorusGeometry(1, 0.035, 3, 32), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.62, depthWrite: false }), 170);
  const beams = mesh(new THREE.BoxGeometry(0.035, 0.04, 1), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.75, depthWrite: false }), 180);
  const sparks = mesh(new THREE.OctahedronGeometry(0.10), new THREE.MeshBasicMaterial({ color: 0xffe2a9 }), 100);
  const zoneMesh = mesh(new THREE.RingGeometry(0.91, 1, 40), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }), 100);
  const zoneFill = mesh(new THREE.CircleGeometry(1, 32), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }), 100);
  const warningGlyphs = mesh(new THREE.RingGeometry(0.18, 0.3, 3), new THREE.MeshBasicMaterial({ color: 0xffd7b2, side: THREE.DoubleSide, depthWrite: false }), 100);
  const shotMesh = mesh(new THREE.IcosahedronGeometry(0.18, 0), new THREE.MeshBasicMaterial({ color: 0xffbdce }), 180);
  const destination = mesh(new THREE.TorusGeometry(0.4, 0.04, 3, 24), new THREE.MeshBasicMaterial({ color: 0xe7dfb5, transparent: true, opacity: 0.7 }));
  destination.rotation.x = Math.PI / 2;
  const reachRing = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 128 }, (_, i) => new THREE.Vector3(Math.cos(i / 128 * Math.PI * 2), 0, Math.sin(i / 128 * Math.PI * 2)))), new THREE.LineBasicMaterial({ color: 0xf1cf82, transparent: true, opacity: 0.22, depthWrite: false }));
  scene.add(reachRing); owned.push(reachRing);
  const captureMarker = mesh(new THREE.TorusGeometry(0.9, 0.075, 4, 32), new THREE.MeshBasicMaterial({ color: 0xffe7a9, depthTest: false }));
  captureMarker.rotation.x = Math.PI / 2; captureMarker.renderOrder = 4;
  const counts = {}, batches = {}, modelIds = Object.keys(TYPES);
  for (const type of modelIds) {
    batches[type] = createAssetBatch(library.get(type), type === "boss" ? 1 : 246);
    scene.add(batches[type].group);
  }
  const allyOrigins = new Map(), allyTargets = new Map(), dummy = new THREE.Object3D(), color = new THREE.Color();
  const ray = new THREE.Raycaster(), plane = new THREE.Plane(up, 0), hit = new THREE.Vector3(), pointer = new THREE.Vector2();
  function matrix(target, i, x, y, z, sx = 1, sy = sx, sz = sx, rx = 0, ry = 0) {
    dummy.position.set(x, y, z); dummy.scale.set(sx, sy, sz); dummy.rotation.set(rx, ry, 0); dummy.updateMatrix(); target.setMatrixAt(i, dummy.matrix);
  }
  function pose(name, type, time, id, attack = 0, wind = 0) {
    if (settings.reducedMotion) return;
    const flap = Math.sin(time * (type === "volt" ? 10 : 5) + id) * 0.26;
    if (name === "wing_l") return { axis: "z", angle: flap + attack * 0.12 };
    if (name === "wing_r") return { axis: "z", angle: -flap - attack * 0.12 };
    if (name === "head") return { axis: "x", angle: -wind * 0.19 + attack * 0.13 };
    if (name === "jaw") return { axis: "x", angle: attack * 0.22 + wind * 0.12 };
    if (name === "clapper") return { axis: "x", angle: Math.sin(time * 3) * 0.1 + attack * 0.23 };
    if (name === "arm_l" || name === "arm_r") return { axis: "x", angle: -wind * 0.5 + attack * 0.3 };
  }
  let viewWidth = 0, viewHeight = 0;
  const planningTarget = new THREE.Vector3();
  function resize() {
    const { width, height } = container.getBoundingClientRect(); viewWidth = width; viewHeight = height;
    renderer.setSize(width, height); fitGameCamera(camera, width, height);
  }
  const resizeObserver = new ResizeObserver(resize); resizeObserver.observe(container); resize();
  function render(s, modal = null, highlightedId = null, planningWidth = 0) {
    if (modal === "capture" && planningWidth > 0) {
      renderer.setViewport(0, 0, planningWidth, viewHeight);
      planningTarget.set(s.player.x, 0, s.player.z);
      fitGameCamera(camera, planningWidth, viewHeight, { halfHeight: Math.max(18, 14.5 / (planningWidth / viewHeight)), target: planningTarget });
    } else { renderer.setViewport(0, 0, viewWidth, viewHeight); fitGameCamera(camera, viewWidth, viewHeight); }
    const motion = settings.reducedMotion ? 0 : 1;
    allyOrigins.clear(); allyTargets.clear();
    for (const effect of s.effects) if (effect.sourceId) allyTargets.set(effect.sourceId, effect);
    for (const type of modelIds) counts[type] = 0;
    player.position.set(s.player.x, Math.max(0, Math.sin(s.time * 7) * 0.035) * motion, s.player.z);
    if (s.target) player.rotation.y = Math.atan2(s.target.x - s.player.x, s.target.z - s.player.z);
    else if (s.keys.x || s.keys.z) player.rotation.y = Math.atan2(s.keys.x, s.keys.z);
    arm.quaternion.copy(armNeutral).multiply(q.setFromAxisAngle(up, Math.sin(s.time * 2) * 0.035 * motion));
    player.updateMatrixWorld(true); captureSocket.getWorldPosition(lightOrigin);
    lanternLight.intensity = 0.6 + s.charge * 1.8;
    halo.position.set(s.player.x, 0.035, s.player.z);
    halo.material.color.setHex(s.invuln > 0 ? 0xf09da6 : 0xf7dca7);
    let ns = 0;
    matrix(shadows, ns++, s.player.x, 0.012, s.player.z, 1, 1, 1, -Math.PI / 2);
    for (const e of s.enemies) {
      const bob = Math.max(0, Math.sin(s.time * (e.type === "volt" ? 11 : 6) + e.id)) * 0.045 * motion;
      const wind = e.type === "boss" ? Math.max(0, 1 - e.clock / 0.7) : e.wind > 0 ? 1 : 0;
      const attack = e.type === "boss" ? Math.max(0, (e.clock - 2.9) / 0.6) : e.dash > 0 ? 1 : 0;
      p.set(e.x, bob, e.z); q.setFromAxisAngle(up, Math.atan2(s.player.x - e.x, s.player.z - e.z)); scale.setScalar(1);
      batches[e.type].set(counts[e.type]++, p, q, scale, (name) => pose(name, e.type, s.time, e.id, attack, wind));
      const r = e.type === "boss" ? 2.3 : 1;
      matrix(shadows, ns++, e.x, 0.014, e.z, r, r, r, -Math.PI / 2);
    }
    s.squad.forEach((a, i) => {
      const theta = i / Math.max(1, s.squad.length) * Math.PI * 2 + s.time * 0.2 * motion;
      const r = TYPES[a.type].tier ? 2.6 : 2;
      const x = s.player.x + Math.cos(theta) * r, z = s.player.z + Math.sin(theta) * r;
      const aim = allyTargets.get(a.id), attack = aim ? aim.life / aim.max : 0;
      allyOrigins.set(a.id, { x, z });
      p.set(x, 0.12 + Math.sin(s.time * 4 + i) * 0.045 * motion, z);
      q.setFromAxisAngle(up, aim ? Math.atan2((aim.tx ?? aim.x) - x, (aim.tz ?? aim.z) - z) : theta + Math.PI / 2);
      scale.setScalar(0.85);
      batches[a.type].set(counts[a.type]++, p, q, scale, (name) => pose(name, a.type, s.time, a.id, attack));
      const ringScale = TYPES[a.type].tier ? 1.6 : 1;
      matrix(allyRings, i, x, 0.055, z, ringScale, ringScale, ringScale, Math.PI / 2);
      matrix(shadows, ns++, x, 0.014, z, ringScale, ringScale, ringScale, -Math.PI / 2);
    });
    shadows.count = ns; shadows.instanceMatrix.needsUpdate = true;
    allyRings.count = s.squad.length; allyRings.instanceMatrix.needsUpdate = true;
    for (const type of modelIds) batches[type].commit(counts[type]);
    let nr = 0, nb = 0, np = 0;
    const addRing = (x, z, radius, tint, y = 0.07) => {
      if (nr >= 170) return;
      matrix(fxRings, nr, x, y, z, radius, radius, radius, Math.PI / 2); fxRings.setColorAt(nr++, color.setHex(tint));
    };
    for (const f of s.effects) {
      const origin = allyOrigins.get(f.sourceId);
      const ox = origin?.x ?? lightOrigin.x, oz = origin?.z ?? lightOrigin.z;
      if (f.kind === "beam" && nb < 180) {
        const d = Math.hypot(f.tx - ox, f.tz - oz);
        matrix(beams, nb, (ox + f.tx) / 2, 0.85, (oz + f.tz) / 2, 1, 1, d, 0, Math.atan2(f.tx - ox, f.tz - oz));
        beams.setColorAt(nb++, color.setHex(f.color));
      } else {
        const progress = 1 - f.life / f.max;
        const radius = f.r * (settings.reducedMotion ? 0.7 : 0.3 + 0.7 * progress);
        addRing(f.x, f.z, radius, f.color);
        if (["bind", "evolve"].includes(f.kind) && motion) {
          if (f.kind === "evolve") addRing(f.x, f.z, radius * 0.82, 0xffe8b9, 0.11);
          for (let i = 0; i < (f.kind === "evolve" ? 24 : 9) && np < 100; i++) {
            const angle = i * 2.39996 + progress * 0.6;
            const r = f.kind === "evolve" ? radius * (0.65 + (i % 3) * 0.12) : (1 - progress) * 1.6;
            matrix(sparks, np++, f.x + Math.cos(angle) * r, 0.25 + Math.sin(progress * Math.PI) * (1 + i % 4 * 0.4), f.z + Math.sin(angle) * r);
          }
        }
      }
    }
    for (const e of s.enemies) if (e.wind > 0) {
      addRing(e.x, e.z, 1.15, 0xff8f86);
      if (nb < 180) {
        matrix(beams, nb, e.x + e.dx * 1.1, 0.08, e.z + e.dz * 1.1, 2.2, 1, 2.2, 0, Math.atan2(e.dx, e.dz));
        beams.setColorAt(nb++, color.setHex(0xff8f86));
      }
    }
    for (const [id, origin] of allyOrigins) if (allyTargets.has(id)) addRing(origin.x, origin.z, 0.72, 0xb9f4de, 0.12);
    fxRings.count = nr; beams.count = nb; sparks.count = np;
    for (const target of [fxRings, beams, sparks]) { target.instanceMatrix.needsUpdate = true; if (target.instanceColor) target.instanceColor.needsUpdate = true; }
    zoneMesh.count = zoneFill.count = warningGlyphs.count = Math.min(s.zones.length, 100);
    for (let i = 0; i < zoneMesh.count; i++) {
      const z = s.zones[i], warning = z.wind > 0, tint = warning ? 0xffd1a0 : z.r > 4 ? 0xff7088 : 0xad88df;
      matrix(zoneMesh, i, z.x, 0.035, z.z, z.r, z.r, z.r, Math.PI / 2);
      matrix(zoneFill, i, z.x, 0.026, z.z, z.r, z.r, z.r, -Math.PI / 2);
      matrix(warningGlyphs, i, z.x, 0.05, z.z, warning ? 1.6 : 0.01, warning ? 1.6 : 0.01, warning ? 1.6 : 0.01, -Math.PI / 2);
      zoneMesh.setColorAt(i, color.setHex(tint)); zoneFill.setColorAt(i, color);
    }
    for (const target of [zoneMesh, zoneFill, warningGlyphs]) { target.instanceMatrix.needsUpdate = true; if (target.instanceColor) target.instanceColor.needsUpdate = true; }
    shotMesh.count = Math.min(s.shots.length, 180);
    for (let i = 0; i < shotMesh.count; i++) { const b = s.shots[i]; matrix(shotMesh, i, b.x, 0.55, b.z); }
    shotMesh.instanceMatrix.needsUpdate = true;
    destination.visible = !!s.target; if (s.target) destination.position.set(s.target.x, 0.035, s.target.z);
    reachRing.visible = s.phase === "playing" && s.charge >= 1 && (modal === null || modal === "capture");
    reachRing.position.set(s.player.x, 0.04, s.player.z); reachRing.scale.setScalar(s.config.captureRange); reachRing.material.opacity = modal === "capture" ? 0.7 : 0.2;
    const highlighted = s.enemies.find((e) => e.id === highlightedId);
    captureMarker.visible = modal === "capture" && !!highlighted;
    if (highlighted) captureMarker.position.set(highlighted.x, 0.1, highlighted.z);
    renderer.render(scene, camera);
  }
  return {
    renderer, scene, camera, canvas: renderer.domElement, render,
    assets: { manifestVersion: manifest.schemaVersion, count: library.size, models: [...library.values()].map((a) => ({ id: a.id, sha256: a.diagnostics.sha256, triangles: a.diagnostics.triangles, primitives: a.diagnostics.meshes.length })) },
    point(clientX, clientY) {
      renderer.setViewport(0, 0, viewWidth, viewHeight); fitGameCamera(camera, viewWidth, viewHeight);
      const rect = renderer.domElement.getBoundingClientRect(); pointer.set((clientX - rect.left) / rect.width * 2 - 1, -(clientY - rect.top) / rect.height * 2 + 1);
      ray.setFromCamera(pointer, camera); ray.ray.intersectPlane(plane, hit); return { x: hit.x, z: hit.z };
    },
    dispose() {
      resizeObserver.disconnect(); renderer.setAnimationLoop(null);
      for (const batch of [...Object.values(batches), ...environmentBatches]) batch.dispose();
      const geometries = new Set(), materials = new Set();
      for (const item of owned) { geometries.add(item.geometry); materials.add(item.material); }
      for (const g of geometries) g.dispose(); for (const m of materials) m.dispose();
      for (const asset of library.values()) disposeAsset(asset);
      renderer.dispose();
    },
  };
}
