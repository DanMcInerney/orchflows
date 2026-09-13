import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const loader = new GLTFLoader();
function modelUrl(path) {
  const url = new URL(path, location.href);
  if (url.origin !== location.origin || !url.pathname.startsWith("/models/"))
    throw Error(`Asset path must be local /models/: ${path}`);
  return url;
}

export async function loadManifest({ signal } = {}) {
  const response = await fetch("/models/manifest.json", {
    cache: "no-store",
    signal,
  });
  if (!response.ok)
    throw Error(
      `Model manifest is not available (HTTP ${response.status}). Export public/models/manifest.json, then Reload assets.`,
    );
  let manifest;
  try {
    manifest = await response.json();
  } catch {
    throw Error(
      "Model manifest is missing or is not valid JSON. Export public/models/manifest.json, then Reload assets.",
    );
  }
  if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.assets))
    throw Error("Model manifest requires schemaVersion 1 and an assets array.");
  const ids = new Set();
  for (const entry of manifest.assets) {
    if (!entry.id || ids.has(entry.id) || typeof entry.file !== "string")
      throw Error(`Invalid or duplicate asset entry: ${entry.id}`);
    ids.add(entry.id);
    modelUrl(entry.file);
  }
  return manifest;
}

export async function loadAsset(entry, { signal } = {}) {
  const url = modelUrl(entry.file),
    response = await fetch(url, { cache: "no-store", signal });
  if (!response.ok)
    throw Error(
      `${entry.id}: GLB request failed (HTTP ${response.status}): ${entry.file}`,
    );
  const bytes = await response.arrayBuffer(),
    header = new DataView(bytes);
  if (
    bytes.byteLength < 20 ||
    header.getUint32(0, true) !== 0x46546c67 ||
    header.getUint32(4, true) !== 2
  )
    throw Error(
      `${entry.id}: expected a binary glTF 2 file, received invalid content.`,
    );
  let gltf;
  try {
    gltf = await loader.parseAsync(bytes, new URL(".", url).href);
  } catch (error) {
    throw Error(`${entry.id}: glTF import failed: ${error.message}`);
  }
  if (signal?.aborted) {
    disposeAsset({ scene: gltf.scene });
    throw new DOMException("Asset load cancelled", "AbortError");
  }
  const root = gltf.scene.getObjectByName(entry.root || entry.id);
  if (!root) {
    disposeAsset({ scene: gltf.scene });
    throw Error(
      `${entry.id}: required root node "${entry.root || entry.id}" is absent.`,
    );
  }
  gltf.scene.updateMatrixWorld(true);
  const inspected = inspectAsset(gltf, bytes.byteLength);
  if (!inspected.meshes.length) {
    disposeAsset({ scene: gltf.scene });
    throw Error(`${entry.id}: no visible mesh primitives were exported.`);
  }
  if (inspected.skinnedMeshes) {
    disposeAsset({ scene: gltf.scene });
    throw Error(
      `${entry.id}: skinned meshes cannot use the agreed rigid instancing path.`,
    );
  }
  const warnings = [];
  if (entry.triangles && entry.triangles !== inspected.triangles)
    warnings.push(
      `Manifest triangles ${entry.triangles}; runtime ${inspected.triangles}.`,
    );
  if (inspected.animations.length)
    warnings.push(
      "Unexpected GLB clips: rigid procedural motion was the agreed baseline.",
    );
  const digest = await crypto.subtle.digest("SHA-256", bytes),
    sha256 = Array.from(new Uint8Array(digest), (n) =>
      n.toString(16).padStart(2, "0"),
    ).join("");
  if (entry.sha256 && entry.sha256 !== sha256)
    warnings.push("Manifest SHA-256 differs from the loaded GLB.");
  return {
    id: entry.id,
    entry,
    scene: gltf.scene,
    animations: gltf.animations,
    diagnostics: {
      id: entry.id,
      file: entry.file,
      ...inspected,
      sha256,
      warnings,
    },
  };
}

export function inspectAsset(gltf, bytes = 0) {
  const materials = new Set(),
    textures = new Set(),
    meshes = [],
    sockets = [];
  let triangles = 0,
    vertices = 0,
    skinnedMeshes = 0;
  gltf.scene.updateMatrixWorld(true);
  gltf.scene.traverse((node) => {
    if (node.name.startsWith("socket_"))
      sockets.push({
        name: node.name,
        parent: node.parent?.name,
        local: {
          translation: node.position.toArray(),
          quaternion: node.quaternion.toArray(),
          scale: node.scale.toArray(),
        },
        world: new THREE.Vector3()
          .setFromMatrixPosition(node.matrixWorld)
          .toArray(),
      });
    if (!node.isMesh) return;
    const count =
      (node.geometry.index?.count ?? node.geometry.attributes.position.count) /
      3;
    triangles += count;
    vertices += node.geometry.attributes.position.count;
    if (node.isSkinnedMesh) skinnedMeshes++;
    meshes.push({
      name: node.name,
      parent: node.parent?.name,
      triangles: count,
      vertices: node.geometry.attributes.position.count,
      vertexColors: !!node.geometry.attributes.color,
      local: {
        translation: node.position.toArray(),
        quaternion: node.quaternion.toArray(),
        scale: node.scale.toArray(),
      },
    });
    for (const material of Array.isArray(node.material)
      ? node.material
      : [node.material]) {
      materials.add(material);
      for (const value of Object.values(material))
        if (value?.isTexture) textures.add(value);
    }
  });
  const box = new THREE.Box3().setFromObject(gltf.scene);
  return {
    bytes,
    triangles,
    vertices,
    skinnedMeshes,
    bounds: {
      min: box.min.toArray(),
      max: box.max.toArray(),
      size: box.getSize(new THREE.Vector3()).toArray(),
    },
    meshes,
    materials: [...materials].map((m) => ({
      name: m.name,
      type: m.type,
      color: m.color?.getHexString(),
      roughness: m.roughness,
      metalness: m.metalness,
      transparent: m.transparent,
      opacity: m.opacity,
      vertexColors: m.vertexColors,
    })),
    textures: [...textures].map((t) => ({
      name: t.name,
      width: t.image?.width || 0,
      height: t.image?.height || 0,
      estimatedRGBABytes: (t.image?.width || 0) * (t.image?.height || 0) * 4,
    })),
    sockets,
    animations: (gltf.animations || []).map((a) => ({
      name: a.name,
      duration: a.duration,
      tracks: a.tracks.map((t) => t.name),
    })),
  };
}

export function cloneAsset(asset) {
  return asset.scene.clone(true);
}

// Each exported rigid mesh primitive gets one batch. Shared geometry/materials
// remain owned by the loaded asset. Node hierarchy and hinge transforms survive.
export function createAssetBatch(asset, capacity) {
  const group = new THREE.Group(),
    nodes = [],
    parts = [],
    indexByNode = new Map();
  asset.scene.traverse((node) => {
    const index = nodes.length;
    indexByNode.set(node, index);
    nodes.push({
      name: node.name,
      parent: indexByNode.get(node.parent) ?? -1,
      position: node.position.clone(),
      quaternion: node.quaternion.clone(),
      scale: node.scale.clone(),
      world: new THREE.Matrix4(),
      local: new THREE.Matrix4(),
    });
    if (node.isMesh) {
      const mesh = new THREE.InstancedMesh(
        node.geometry,
        node.material,
        capacity,
      );
      mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      mesh.frustumCulled = false;
      mesh.count = 0;
      group.add(mesh);
      parts.push({ node: index, mesh });
    }
  });
  const entity = new THREE.Matrix4(),
    final = new THREE.Matrix4(),
    rotation = new THREE.Quaternion(),
    posed = new THREE.Quaternion(),
    axis = new THREE.Vector3();
  return {
    group,
    capacity,
    parts,
    set(index, position, quaternion, scale, pose) {
      if (index < 0 || index >= capacity)
        throw Error(`Instance capacity exceeded: ${asset.id}`);
      entity.compose(position, quaternion, scale);
      for (const node of nodes) {
        posed.copy(node.quaternion);
        const motion = pose?.(node.name);
        if (motion) {
          axis.set(
            motion.axis === "x" ? 1 : 0,
            motion.axis === "y" ? 1 : 0,
            motion.axis === "z" ? 1 : 0,
          );
          rotation.setFromAxisAngle(axis, motion.angle);
          posed.multiply(rotation);
        }
        node.local.compose(node.position, posed, node.scale);
        if (node.parent < 0) node.world.copy(node.local);
        else node.world.multiplyMatrices(nodes[node.parent].world, node.local);
      }
      for (const part of parts) {
        final.multiplyMatrices(entity, nodes[part.node].world);
        part.mesh.setMatrixAt(index, final);
      }
    },
    commit(count) {
      for (const part of parts) {
        part.mesh.count = count;
        part.mesh.instanceMatrix.needsUpdate = true;
      }
    },
    dispose() {
      group.removeFromParent();
      for (const part of parts) part.mesh.dispose();
    },
  };
}

export function disposeAsset(asset) {
  const geometry = new Set(),
    materials = new Set(),
    textures = new Set();
  asset.scene?.traverse((node) => {
    if (!node.isMesh) return;
    geometry.add(node.geometry);
    for (const m of Array.isArray(node.material)
      ? node.material
      : [node.material]) {
      materials.add(m);
      for (const value of Object.values(m))
        if (value?.isTexture) textures.add(value);
    }
  });
  for (const t of textures) t.dispose();
  for (const m of materials) m.dispose();
  for (const g of geometry) g.dispose();
}
