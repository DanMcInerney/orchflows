/**
 * Package-owned, one-shot asset validation boundary.
 *
 * Each invocation reads the exact GLB bytes supplied by the runner and
 * writes a fresh JSON report. The loader mode is owned by this package: it
 * serves the declared target Three.js modules into a package-generated page,
 * observes the live browser scene, and never accepts a caller-supplied pass
 * boolean or validator executable.
 */
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import { basename, extname, isAbsolute, relative, resolve } from "node:path";

const EXIT_OK = 0;
const EXIT_INVALID = 2;
const EXIT_CAPABILITY = 3;
const EXIT_EVIDENCE = 4;
const EXIT_TIMEOUT = 5;

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`${name} is required`);
  return process.argv[index + 1];
}

function sha256(bytes) {
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, { flag: "wx" });
}

async function overwriteJson(path, value) {
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`);
}

async function readJsonObject(path, label) {
  let value;
  try { value = JSON.parse(await readFile(path, "utf8")); } catch (error) { throw new Error(`${label} is not valid JSON: ${error.message}`); }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value;
}

function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

function semanticExpectations(job, manifest) {
  return {
    job_id: job.id,
    artifact_commit: job.artifact_commit,
    job_declarations: {
      scene: job.scene,
      budgets: job.budgets,
      colliders: job.colliders || [],
      attachments: job.attachments || [],
      material_roles: job.material_roles || {},
      animation_clips: job.animation_clips || [],
      required_extensions: job.required_extensions || [],
    },
    manifest_declarations: {
      units: manifest.units,
      unit_scale: manifest.unit_scale,
      up_axis: manifest.up_axis,
      gameplay_forward: manifest.gameplay_forward,
      origin: manifest.origin,
      colliders: manifest.colliders,
      attachments: manifest.attachments,
      material_roles: manifest.material_roles,
      animation_clips: manifest.animation_clips,
      required_extensions: manifest.required_extensions,
      semantic_contract: manifest.semantic_contract,
    },
  };
}

function semanticExpectationsHash(job, manifest) {
  return sha256(Buffer.from(canonical(semanticExpectations(job, manifest))));
}

function finiteArray(value, length, label) {
  if (!Array.isArray(value) || value.length !== length || value.some(item => typeof item !== "number" || !Number.isFinite(item))) throw new Error(`${label} must contain ${length} finite numbers`);
  return value;
}

function closeNumber(actual, expected, tolerance) {
  return Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= tolerance;
}

function closeVector(actual, expected, tolerance) {
  return Array.isArray(actual) && Array.isArray(expected) && actual.length === expected.length && actual.every((value, index) => closeNumber(value, expected[index], tolerance));
}

function closeMatrix(actual, expected, tolerance) {
  return Array.isArray(actual) && Array.isArray(expected) && actual.length === expected.length && actual.every((value, index) => closeNumber(value, expected[index], tolerance));
}

function conversionContract() {
  return { matrix: "Rx(-pi/2)", mapping: "(x,y,z)->(x,z,-y)", source_up: "+Z", runtime_up: "+Y" };
}

function reportResult(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function contained(root, candidate, label) {
  const rootPath = resolve(root);
  const target = resolve(rootPath, candidate);
  const rel = relative(rootPath, target);
  if (!rel || rel.startsWith("..") || isAbsolute(rel)) throw new Error(`${label} escapes target workspace`);
  return target;
}

async function runKhronos() {
  const glbPath = resolve(argument("--glb"));
  const reportPath = resolve(argument("--report"));
  const artifactCommit = argument("--artifact-commit");
  const jobId = argument("--job-id");
  const bytes = await readFile(glbPath);
  if (!bytes.length) throw new Error("GLB is empty");
  let imported;
  try { imported = await import("gltf-validator"); } catch (error) {
    process.stderr.write(`pinned glTF Validator is unavailable: ${error.message}\n`);
    process.exitCode = EXIT_CAPABILITY;
    return;
  }
  const validator = imported.default?.validateBytes ? imported.default : imported;
  if (typeof validator.validateBytes !== "function") throw new Error("pinned glTF Validator has no validateBytes API");
  const report = await validator.validateBytes(new Uint8Array(bytes), { format: "glb", maxIssues: 0, writeTimestamp: false });
  const errors = report?.issues?.numErrors;
  if (!Number.isInteger(errors)) throw new Error("Khronos report did not contain issues.numErrors");
  const output = {
    ...report,
    orchflows: {
      kind: "khronos-validation",
      job_id: jobId,
      artifact_commit: artifactCommit,
      glb_hash: sha256(bytes),
      source: "package-owned-fresh-process",
      validator: "gltf-validator@2.0.0-dev.3.10",
    },
  };
  await writeJson(reportPath, output);
  const result = { status: errors === 0 ? "pass" : "fail", errors, export_sha256: sha256(bytes), report_path: reportPath, report_sha256: sha256(Buffer.from(`${JSON.stringify(output, null, 2)}\n`)), validator: "gltf-validator@2.0.0-dev.3.10" };
  reportResult(result);
  if (errors !== 0) process.exitCode = EXIT_EVIDENCE;
}

async function runLoader() {
  const glbPath = resolve(argument("--glb"));
  const reportPath = resolve(argument("--report"));
  const workspace = resolve(argument("--workspace"));
  const threeRelative = argument("--three-root");
  const browserExecutable = resolve(argument("--browser-executable"));
  const artifactCommit = argument("--artifact-commit");
  const jobId = argument("--job-id");
  const jobPath = resolve(argument("--job"));
  const manifestPath = resolve(argument("--manifest"));
  const timeoutMs = Number(argument("--timeout-ms"));
  const threeRoot = contained(workspace, threeRelative, "Three.js package");
  const threeModule = contained(threeRoot, "build/three.module.js", "Three.js module");
  const loaderModule = contained(threeRoot, "examples/jsm/loaders/GLTFLoader.js", "GLTFLoader module");
  const [glbBytes, threeBytes, loaderBytes, jobBytes] = await Promise.all([readFile(glbPath), readFile(threeModule), readFile(loaderModule), readFile(jobPath)]);
  if (!glbBytes.length || !threeBytes.length || !loaderBytes.length) throw new Error("GLB, Three.js, or GLTFLoader module is empty");
  if (!isAbsolute(browserExecutable)) throw new Error("browser executable must be absolute");
  const job = JSON.parse(jobBytes.toString("utf8"));
  const manifest = await readJsonObject(manifestPath, "asset manifest");
  if (job.id !== jobId || job.artifact_commit !== artifactCommit || manifest.artifact_commit !== artifactCommit) throw new Error("job, manifest, and validator artifact identities do not match");
  if (manifest.exported_glb_sha256 !== sha256(glbBytes)) throw new Error("asset manifest GLB hash does not match validator input");
  const scene = job.scene || {};
  const manifestScene = { units: manifest.units, unit_scale: manifest.unit_scale, up_axis: manifest.up_axis, gameplay_forward: manifest.gameplay_forward, origin: manifest.origin };
  const expectedScene = { units: scene.units, unit_scale: scene.unit_scale, up_axis: scene.up_axis, gameplay_forward: scene.gameplay_forward, origin: scene.origin };
  const declarations = { colliders: job.colliders || [], attachments: job.attachments || [], material_roles: job.material_roles || {}, animation_clips: job.animation_clips || [], required_extensions: job.required_extensions || [] };
  const manifestDeclarations = { colliders: manifest.colliders, attachments: manifest.attachments, material_roles: manifest.material_roles, animation_clips: manifest.animation_clips, required_extensions: manifest.required_extensions };
  if (canonical(manifestScene) !== canonical(expectedScene) || canonical(manifestDeclarations) !== canonical(declarations)) throw new Error("asset manifest declarations do not match the frozen job");
  const expectedContract = manifest.semantic_contract;
  if (canonical(expectedContract?.coordinate_conversion) !== canonical(conversionContract()) || Number(expectedContract?.tolerance) !== 1e-4) throw new Error("asset manifest coordinate conversion contract is missing or changed");
  const jobHash = sha256(jobBytes);
  const expectationsHash = semanticExpectationsHash(job, manifest);
  const glbHash = sha256(glbBytes);
  const loaderPage = `<!doctype html><meta charset="utf-8"><canvas id="canvas" width="320" height="240"></canvas><script type="importmap">${JSON.stringify({ imports: { three: "/three/build/three.module.js", "three/addons/": "/three/examples/jsm/" } })}</script><script type="module">
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
const EXPECTATIONS = ${JSON.stringify({ scene: expectedScene, declarations, budgets: job.budgets || {}, frame_rate: scene.frame_rate || 24, coordinate_conversion: conversionContract(), tolerance: 1e-4 })};
const result = { checks: { scale: "fail", material: "fail", animation: "fail", collider: "fail" }, semantic_checks: {}, meshes: 0, materials: 0, animations: 0, textures: 0, draw_calls: 0, three_revision: THREE.REVISION, loader: "GLTFLoader" };
const tolerance = EXPECTATIONS.tolerance;
const close = (actual, expected, epsilon=tolerance) => Number.isFinite(actual) && Number.isFinite(expected) && Math.abs(actual - expected) <= epsilon;
const closeVector = (actual, expected, epsilon=tolerance) => Array.isArray(actual) && Array.isArray(expected) && actual.length === expected.length && actual.every((value, index) => close(value, expected[index], epsilon));
const closeMatrix = (actual, expected, epsilon=tolerance) => Array.isArray(actual) && Array.isArray(expected) && actual.length === expected.length && actual.every((value, index) => close(value, expected[index], epsilon));
const declarationTolerance = declaration => Math.min(tolerance, Number(declaration.tolerance || tolerance));
const declarationName = declaration => declaration.name || declaration.object;
const conversion = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
const inverseConversion = conversion.clone().invert();
function expectedMatrix(declaration) {
  const position = declaration.position || [0, 0, 0];
  const rotation = declaration.rotation || [0, 0, 0];
  const scale = declaration.scale || [1, 1, 1];
  const source = new THREE.Matrix4().compose(new THREE.Vector3(...position), new THREE.Quaternion().setFromEuler(new THREE.Euler(...rotation, "XYZ")), new THREE.Vector3(...scale));
  return declaration.coordinate_space === "runtime-world" ? source : conversion.clone().multiply(source).multiply(inverseConversion);
}
function matrixOf(object) { object.updateMatrixWorld(true); return object.matrixWorld.elements.slice(); }
function finiteMatrix(matrix) { return Array.isArray(matrix) && matrix.length === 16 && matrix.every(Number.isFinite); }
function runtimeBounds(bounds, coordinateSpace) {
  if (coordinateSpace === "runtime-world") return bounds;
  const corners = []; for (const x of [bounds[0], bounds[3]]) for (const y of [bounds[1], bounds[4]]) for (const z of [bounds[2], bounds[5]]) corners.push(new THREE.Vector3(x, y, z).applyMatrix4(conversion).toArray());
  return [0, 1, 2].map(axis => Math.min(...corners.map(point => point[axis]))).concat([0, 1, 2].map(axis => Math.max(...corners.map(point => point[axis]))));
}
function observeObject(object) {
  const box = new THREE.Box3().setFromObject(object);
  const dimensions = box.getSize(new THREE.Vector3());
  return { name: object.name, matrix: matrixOf(object), position: object.getWorldPosition(new THREE.Vector3()).toArray(), scale: object.getWorldScale(new THREE.Vector3()).toArray(), bounds: [...box.min.toArray(), ...box.max.toArray()], dimensions: dimensions.toArray(), parent: object.parent?.name || null, materials: object.isMesh ? (Array.isArray(object.material) ? object.material.map(item => item?.name || "") : [object.material?.name || ""]) : [] };
}
function semanticResult(status, basis, observed={}) { return { status, basis, observed }; }
function compareTransform(declaration, observed, label) {
  const epsilon = declarationTolerance(declaration);
  const failures = [];
  const expected = expectedMatrix(declaration).elements;
  if ((declaration.position || declaration.rotation || declaration.scale) && !closeMatrix(observed.matrix, expected, epsilon)) failures.push(label + " transform does not match frozen declaration after Blender-to-runtime conversion");
  if (declaration.parent !== undefined && observed.parent !== declaration.parent) failures.push(label + " parent binding does not match frozen declaration");
  if (declaration.dimensions) {
    const dimensions = declaration.coordinate_space === "runtime-world" ? declaration.dimensions : [declaration.dimensions[0], declaration.dimensions[2], declaration.dimensions[1]];
    if (!closeVector(observed.dimensions, dimensions, epsilon)) failures.push(label + " world dimensions do not match frozen declaration");
  }
  if (declaration.bounds && !closeVector(observed.bounds, runtimeBounds(declaration.bounds, declaration.coordinate_space), epsilon)) failures.push(label + " world bounds do not match frozen declaration");
  return failures;
}
function findObjects(scene) { const values = new Map(); scene.traverse(object => { if (object.name && !values.has(object.name)) values.set(object.name, object); }); return values; }
try {
  const loadStarted = performance.now();
  const renderer = new THREE.WebGLRenderer({ canvas: document.querySelector("#canvas"), antialias: false });
  renderer.setSize(320, 240, false);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0.008, 0.012, 0.025);
  scene.add(new THREE.HemisphereLight(0x9fc8ff, 0x101828, 1.5));
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.5); keyLight.position.set(4, 6, 8); scene.add(keyLight);
  const camera = new THREE.PerspectiveCamera(45, 4 / 3, 0.01, 1000);
  camera.position.set(3, 2, 5); camera.lookAt(0, 0, 0);
  new GLTFLoader().load("/asset.glb", (gltf) => {
    const objects = findObjects(gltf.scene);
    const meshObjects = []; const materialObjects = new Map(); let finite = true; let globalBox = new THREE.Box3();
    gltf.scene.traverse((object) => {
      if (!object.isMesh) return;
      meshObjects.push(object); result.meshes += 1;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      result.materials += materials.filter(Boolean).length; result.draw_calls += Math.max(1, object.geometry?.groups?.length || 0);
      finite = finite && [object.scale.x, object.scale.y, object.scale.z, object.position.x, object.position.y, object.position.z, ...matrixOf(object)].every(Number.isFinite);
      const objectBox = new THREE.Box3().setFromObject(object); globalBox.union(objectBox);
      for (const material of materials.filter(Boolean)) { const name = material.name || ""; const entry = materialObjects.get(name) || { objects: [], roles: [] }; entry.objects.push(object.name); const role = material.userData?.orchflows_role || material.userData?.role; if (role) entry.roles.push(role); materialObjects.set(name, entry); }
    });
    result.animations = gltf.animations.length; result.load_time_ms = performance.now() - loadStarted;
    const textures = new Set(); for (const material of materialObjects.keys()) { const object = [...meshObjects].find(mesh => (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).some(item => item?.name === material)); for (const item of (object ? (Array.isArray(object.material) ? object.material : [object.material]) : [])) for (const value of Object.values(item || {})) if (value?.isTexture) textures.add(value); } result.textures = textures.size;
    result.objects = [...objects.values()].map(observeObject); result.material_bindings = Object.fromEntries(materialObjects);
    const boundsValues = [...globalBox.min.toArray(), ...globalBox.max.toArray()];
    result.semantic_checks.scale = semanticResult(finite && result.meshes > 0 ? "pass" : "fail", "actual Three.js Object3D matrices and mesh presence", { meshes: result.meshes });
    result.semantic_checks.bounds = semanticResult(globalBox.isEmpty() || boundsValues.some(value => !Number.isFinite(value)) ? "fail" : "pass", "actual THREE.Box3 world bounds from loaded meshes", { bounds: boundsValues });
    result.semantic_checks.orientation = semanticResult(EXPECTATIONS.scene.up_axis === "+Y" && result.objects.every(object => finiteMatrix(object.matrix)) ? "pass" : "fail", "loaded matrixWorld values are finite in Three.js +Y world", { up_axis: EXPECTATIONS.scene.up_axis });
    const materialFailures = [];
    for (const [materialName, declaration] of Object.entries(EXPECTATIONS.declarations.material_roles)) {
      const binding = materialObjects.get(materialName);
      if (!binding) { if (typeof declaration === "object" && declaration.optional === true) continue; materialFailures.push("material role " + materialName + " is missing from loaded GLTF materials"); continue; }
      const role = typeof declaration === "string" ? declaration : declaration.role;
      const requiredObjects = typeof declaration === "string" ? null : declaration.objects;
      if (!binding.objects.length || (requiredObjects && requiredObjects.some(name => !binding.objects.includes(name)))) materialFailures.push("material role " + materialName + " is not bound to its declared mesh object(s)");
      if (role && binding.roles.length && !binding.roles.includes(role)) materialFailures.push("material role " + materialName + " has a mismatched runtime role");
    }
    result.semantic_checks.material = semanticResult(materialFailures.length ? "fail" : "pass", "loaded material names and object bindings", { bindings: result.material_bindings, failures: materialFailures });
    const compareObjects = (items, label) => { if (!items.length) return semanticResult("not_applicable", "job declared no " + label + "; no " + label + " semantics were fabricated"); const failures = []; const observed = []; const optional = []; for (const declaration of items) { const name = declarationName(declaration); const object = objects.get(name); if (!object) { if (declaration.optional === true) { optional.push(name); continue; } failures.push(label + " " + name + " is missing from loaded scene"); continue; } const record = observeObject(object); observed.push(record); failures.push(...compareTransform(declaration, record, label + "/" + name)); } const status = failures.length ? "fail" : (observed.length ? "pass" : "not_applicable"); return semanticResult(status, "actual loaded " + label + " object transforms and world bounds; optional omissions are explicit", { items: observed, optional_absent: optional, failures }); };
    result.semantic_checks.attachments = compareObjects(EXPECTATIONS.declarations.attachments, "attachment");
    result.semantic_checks.collider = compareObjects(EXPECTATIONS.declarations.colliders, "collider");
    if (!EXPECTATIONS.declarations.animation_clips.length) result.semantic_checks.animation = semanticResult("not_applicable", "job declared no animation clips; no playback metric was fabricated");
    else {
      const animationFailures = []; const animationObserved = []; const mixer = new THREE.AnimationMixer(gltf.scene);
      for (const declaration of EXPECTATIONS.declarations.animation_clips) {
        const clip = gltf.animations.find(item => item.name === declaration.name); if (!clip) { if (declaration.optional === true) continue; animationFailures.push("animation clip " + declaration.name + " is missing from loaded GLTF"); continue; }
        const expectedDuration = declaration.duration_seconds ?? ((Number(declaration.end) - Number(declaration.start)) / Number(EXPECTATIONS.frame_rate));
        // glTF exporters may retain the inclusive terminal sample, so the
        // one-frame allowance is the frozen contract. Add a few ulps to keep
        // an exact boundary from failing due to IEEE-754 division rounding.
        const durationTolerance = Math.max(tolerance, 1 / Number(EXPECTATIONS.frame_rate)) + Number.EPSILON * 4;
        const durationOk = close(clip.duration, expectedDuration, durationTolerance);
        const before = new Map(meshObjects.map(object => [object.uuid, matrixOf(object)])); const action = mixer.clipAction(clip); action.reset().play(); mixer.update(Math.max(clip.duration / 3, 1 / Number(EXPECTATIONS.frame_rate))); mixer.update(Math.max(clip.duration / 3, 1 / Number(EXPECTATIONS.frame_rate))); gltf.scene.updateMatrixWorld(true); const changed = meshObjects.some(object => !closeMatrix(before.get(object.uuid), matrixOf(object), tolerance)); action.stop();
        if (!durationOk) animationFailures.push("animation/" + declaration.name + "/duration: observed " + clip.duration + " expected " + expectedDuration); if (!changed) animationFailures.push("animation/" + declaration.name + "/playback: no loaded object transform changed during mixer playback"); animationObserved.push({ name: clip.name, duration: clip.duration, expected_duration: expectedDuration, playback_changed: changed, tracks: clip.tracks.length });
      }
      result.semantic_checks.animation = semanticResult(animationFailures.length ? "fail" : "pass", "GLTFLoader AnimationMixer playback and declared frame timing", { clips: animationObserved, failures: animationFailures });
    }
    const gltfJson = gltf.parser?.json || {}; const usedExtensions = new Set(gltfJson.extensionsUsed || []); const requiredExtensions = EXPECTATIONS.declarations.required_extensions; const extensionFailures = []; const extensionObserved = [];
    for (const extension of requiredExtensions) { const name = typeof extension === "string" ? extension : extension.name; const present = usedExtensions.has(name) || (gltfJson.extensionsRequired || []).includes(name); const handler = gltf.parser?.extensions?.[name] || gltf.parser?.plugins?.[name]; const supported = Boolean(handler); if (!present) extensionFailures.push("required extension " + name + " is absent from GLB extensionsUsed/extensionsRequired"); if (!supported) extensionFailures.push("required extension " + name + " has no GLTFLoader handler/decoder"); extensionObserved.push({ name, present, supported }); }
    result.semantic_checks.extensions = requiredExtensions.length ? semanticResult(extensionFailures.length ? "fail" : "pass", "GLTFLoader parser extension/decoder registry and GLB extension declarations", { extensions: extensionObserved }) : semanticResult("not_applicable", "job declared no required extensions; no decoder metric was fabricated");
    const budget = EXPECTATIONS.budgets; const costFailures = []; if (budget.runtime_bytes !== undefined && ${glbBytes.length} > Number(budget.runtime_bytes)) costFailures.push("runtime_bytes ${glbBytes.length} exceeds " + Number(budget.runtime_bytes)); if (budget.draw_calls !== undefined && result.draw_calls > Number(budget.draw_calls)) costFailures.push("draw_calls " + result.draw_calls + " exceeds " + Number(budget.draw_calls)); if (budget.load_time_ms !== undefined && result.load_time_ms > Number(budget.load_time_ms)) costFailures.push("load_time_ms " + result.load_time_ms + " exceeds " + Number(budget.load_time_ms)); if (budget.mesh_vertices !== undefined && result.meshes <= 0) costFailures.push("mesh_vertices budget cannot be established without loaded meshes");
    result.semantic_checks.cost = semanticResult(costFailures.length ? "fail" : "pass", "declared runtime bytes, draw calls, and load time budgets", { runtime_bytes: ${glbBytes.length}, draw_calls: result.draw_calls, load_time_ms: result.load_time_ms, failures: costFailures });
    const semanticPass = name => result.semantic_checks[name]?.status === "pass" || result.semantic_checks[name]?.status === "not_applicable";
    result.checks = { scale: semanticPass("scale") ? "pass" : "fail", material: semanticPass("material") ? "pass" : "fail", animation: semanticPass("animation") ? "pass" : "fail", collider: semanticPass("collider") ? "pass" : "fail" };
    // Collision geometry is loaded and measured above, then hidden for the
    // consumer capture just as the Blender authoring job hides it in previews.
    for (const declaration of EXPECTATIONS.declarations.colliders) {
      const collider = objects.get(declarationName(declaration));
      if (collider) collider.visible = false;
    }
    scene.add(gltf.scene); renderer.render(scene, camera); window.__loaderResult = result;
  }, undefined, (error) => { result.error = String(error); result.load_time_ms = performance.now(); result.semantic_checks = Object.fromEntries(["scale", "bounds", "orientation", "material", "attachments", "animation", "extensions", "collider", "cost"].map(name => [name, semanticResult("fail", "GLTFLoader load error")])); window.__loaderResult = result; });
} catch (error) { result.error = String(error); window.__loaderResult = result; }
</script>`;
  const mime = { ".js": "text/javascript", ".glb": "model/gltf-binary" };
  const server = createServer(async (request, response) => {
    try {
      const pathname = new URL(request.url, "http://127.0.0.1").pathname;
      if (pathname === "/" || pathname === "/index.html") { response.writeHead(200, { "content-type": "text/html" }); response.end(loaderPage); return; }
      if (pathname === "/asset.glb") { response.writeHead(200, { "content-type": mime[".glb"], "cache-control": "no-store" }); response.end(glbBytes); return; }
      if (pathname.startsWith("/three/")) {
        const file = contained(threeRoot, pathname.slice("/three/".length), "browser module");
        const bytes = await readFile(file); response.writeHead(200, { "content-type": mime[extname(file)] || "text/javascript" }); response.end(bytes); return;
      }
      response.writeHead(404); response.end("not found");
    } catch (error) { response.writeHead(500); response.end(String(error)); }
  });
  await new Promise((resolveListen, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolveListen); });
  let browser;
  let raw;
  try {
    let playwright;
    try { playwright = await import("playwright-core"); } catch (error) { process.stderr.write(`pinned Playwright is unavailable: ${error.message}\n`); process.exitCode = EXIT_CAPABILITY; return; }
    browser = await playwright.chromium.launch({ executablePath: browserExecutable, headless: true, timeout: timeoutMs, args: ["--disable-dev-shm-usage", "--use-angle=swiftshader"] });
    const page = await browser.newPage({ viewport: { width: 320, height: 240 }, deviceScaleFactor: 1 });
    const consoleErrors = [];
    page.on("console", message => { if (message.type() === "error") consoleErrors.push(message.text()); });
    page.on("pageerror", error => consoleErrors.push(String(error)));
    const address = server.address();
    await page.goto(`http://127.0.0.1:${address.port}/index.html`, { waitUntil: "load", timeout: timeoutMs });
    await page.waitForFunction(() => window.__loaderResult !== undefined, { timeout: timeoutMs });
    raw = await page.evaluate(() => window.__loaderResult);
    const screenshot = await page.screenshot();
    const screenshotPath = resolve(reportPath, "..", `${basename(reportPath, extname(reportPath))}.png`);
    await writeFile(screenshotPath, screenshot, { flag: "wx" });
    const screenshotHash = sha256(screenshot);
    raw.browser = { product: browser.version(), executable: browserExecutable, headed: false, viewport: { width: 320, height: 240 }, device_scale_factor: 1, screenshot_sha256: screenshotHash };
    raw.target_probe = { path: basename(screenshotPath), sha256: screenshotHash };
    raw.source = "live-browser";
  } finally {
    await browser?.close().catch(() => {});
    await new Promise(resolveClose => server.close(resolveClose));
  }
  if (!raw || typeof raw !== "object") throw new Error("package browser probe produced no result");
  const expectedChecks = { scale: "pass", material: "pass", animation: "pass", collider: "pass" };
  const semanticNames = ["scale", "bounds", "orientation", "material", "attachments", "animation", "extensions", "collider", "cost"];
  const valid = raw.source === "live-browser" && raw.checks && Object.keys(expectedChecks).every(key => raw.checks[key] === "pass") && raw.semantic_checks && semanticNames.every(key => ["pass", "not_applicable"].includes(raw.semantic_checks[key]?.status));
  const evidence = { schema_version: "1.0.0", kind: "gltf-loader-evidence", id: `${jobId}-gltf-loader`, artifact_commit: artifactCommit, glb_hash: glbHash, job_sha256: jobHash, expectations_hash: expectationsHash, loader: { name: "three", version: String(raw.three_revision || "unknown"), entrypoint: "GLTFLoader" }, coordinate_conversion: conversionContract(), semantic_tolerance: 1e-4, checks: expectedChecks, semantic_checks: raw.semantic_checks, source: "live-browser", target_workspace: workspace, target_three_root: { path: threeRelative, three_module_sha256: sha256(threeBytes), gltf_loader_sha256: sha256(loaderBytes) }, target_probe: raw.target_probe, browser: raw.browser, observed: { meshes: raw.meshes, materials: raw.materials, animations: raw.animations, textures: raw.textures, draw_calls: raw.draw_calls, load_time_ms: raw.load_time_ms }, raw_probe_result: raw };
  if (!valid) { reportResult({ status: "fail", error: "package GLTFLoader browser observation did not pass", export_sha256: glbHash, checks: raw.checks || null }); process.exitCode = EXIT_EVIDENCE; return; }
  await overwriteJson(reportPath, evidence);
  const reportBytes = Buffer.from(`${JSON.stringify(evidence, null, 2)}\n`);
  reportResult({ status: "pass", export_sha256: glbHash, glb_hash: glbHash, evidence_id: evidence.id, evidence_path: reportPath, evidence_sha256: sha256(reportBytes), checks: expectedChecks, target_workspace: workspace, target_three_module_sha256: sha256(threeBytes), target_gltf_loader_sha256: sha256(loaderBytes) });
}

async function main() {
  const mode = process.argv[2];
  if (mode === "khronos") return runKhronos();
  if (mode === "gltf-loader") return runLoader();
  throw new Error("mode must be khronos or gltf-loader");
}

main().catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = EXIT_INVALID; });
