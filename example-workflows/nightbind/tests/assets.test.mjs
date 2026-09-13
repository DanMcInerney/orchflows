import { test } from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import {
  createAssetBatch,
  inspectAsset,
  loadAsset,
  loadManifest,
} from "../src/assets.js";

test("missing manifest and HTML fallback fail visibly instead of masquerading as model success", async () => {
  const originalFetch = globalThis.fetch,
    originalLocation = globalThis.location;
  globalThis.location = {
    href: "http://127.0.0.1:4190/asset-preview.html",
    origin: "http://127.0.0.1:4190",
  };
  globalThis.fetch = async () =>
    new Response("<!doctype html><title>fallback</title>", {
      status: 200,
      headers: { "content-type": "text/html" },
    });
  try {
    await assert.rejects(
      loadManifest(),
      /manifest is missing or is not valid JSON/,
    );
    await assert.rejects(
      loadAsset({ id: "missing", file: "/models/missing.glb" }),
      /expected a binary glTF 2 file/,
    );
  } finally {
    globalThis.fetch = originalFetch;
    if (originalLocation === undefined) delete globalThis.location;
    else globalThis.location = originalLocation;
  }
});

test("rigid GLB batching preserves nested pivots, entity orientation and ally scale", () => {
  const scene = new THREE.Group(),
    body = new THREE.Group(),
    hinge = new THREE.Group();
  body.position.set(0, 1, 0);
  hinge.position.set(1, 0.4, 0);
  hinge.name = "wing_l";
  scene.add(body);
  body.add(hinge);
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(2, 0.1, 0.4),
    new THREE.MeshStandardMaterial(),
  );
  mesh.position.x = 1;
  hinge.add(mesh);
  const batch = createAssetBatch({ id: "fixture", scene }, 2),
    position = new THREE.Vector3(4, 0, 7),
    rotation = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(0, 1, 0),
      Math.PI / 2,
    ),
    scale = new THREE.Vector3(0.85, 0.85, 0.85);
  batch.set(0, position, rotation, scale, (name) =>
    name === "wing_l" ? { axis: "z", angle: 0.3 } : undefined,
  );
  batch.commit(1);
  hinge.rotation.z = 0.3;
  scene.updateMatrixWorld(true);
  const expected = new THREE.Matrix4()
      .compose(position, rotation, scale)
      .multiply(mesh.matrixWorld),
    actual = new THREE.Matrix4();
  batch.parts[0].mesh.getMatrixAt(0, actual);
  for (let i = 0; i < 16; i++)
    assert.ok(Math.abs(expected.elements[i] - actual.elements[i]) < 1e-6);
  assert.equal(batch.parts[0].mesh.count, 1);
  assert.throws(() => batch.set(2, position, rotation, scale), /capacity/);
  batch.dispose();
  mesh.geometry.dispose();
  mesh.material.dispose();
});

test("runtime import inspection counts rendered mesh primitives and attachment transforms", () => {
  const scene = new THREE.Group(),
    material = new THREE.MeshStandardMaterial(),
    mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 2, 3), material);
  mesh.position.y = 1;
  scene.add(mesh);
  const socket = new THREE.Group();
  socket.name = "socket_lantern";
  socket.position.set(0.8, 0.4, 0.2);
  scene.add(socket);
  const result = inspectAsset({ scene, animations: [] }, 1234);
  assert.equal(result.triangles, 12);
  assert.equal(result.materials.length, 1);
  assert.deepEqual(result.bounds.size, [1, 2, 3]);
  assert.deepEqual(result.sockets[0].world, [0.8, 0.4, 0.2]);
  assert.equal(result.bytes, 1234);
  assert.deepEqual(result.animations, []);
  mesh.geometry.dispose();
  material.dispose();
});
