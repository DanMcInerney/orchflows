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
import { extname, isAbsolute, relative, resolve } from "node:path";

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
  const expectedAnimations = Number(argument("--expected-animations"));
  const expectedColliders = Number(argument("--expected-colliders"));
  const timeoutMs = Number(argument("--timeout-ms"));
  const threeRoot = contained(workspace, threeRelative, "Three.js package");
  const threeModule = contained(threeRoot, "build/three.module.js", "Three.js module");
  const loaderModule = contained(threeRoot, "examples/jsm/loaders/GLTFLoader.js", "GLTFLoader module");
  const [glbBytes, threeBytes, loaderBytes] = await Promise.all([readFile(glbPath), readFile(threeModule), readFile(loaderModule)]);
  if (!glbBytes.length || !threeBytes.length || !loaderBytes.length) throw new Error("GLB, Three.js, or GLTFLoader module is empty");
  if (!isAbsolute(browserExecutable)) throw new Error("browser executable must be absolute");
  const glbHash = sha256(glbBytes);
  const loaderPage = `<!doctype html><meta charset="utf-8"><canvas id="canvas" width="320" height="240"></canvas><script type="importmap">${JSON.stringify({ imports: { three: "/three/build/three.module.js", "three/addons/": "/three/examples/jsm/" } })}</script><script type="module">
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
const result = { checks: { scale: "fail", material: "fail", animation: "fail", collider: "fail" }, meshes: 0, materials: 0, animations: 0, three_revision: THREE.REVISION, loader: "GLTFLoader" };
try {
  const renderer = new THREE.WebGLRenderer({ canvas: document.querySelector("#canvas"), antialias: false });
  renderer.setSize(320, 240, false);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 4 / 3, 0.01, 1000);
  camera.position.set(3, 2, 5); camera.lookAt(0, 0, 0);
  new GLTFLoader().load("/asset.glb", (gltf) => {
    let finite = true; let colliderCount = 0;
    gltf.scene.traverse((object) => {
      if (!object.isMesh) return;
      result.meshes += 1;
      result.materials += Array.isArray(object.material) ? object.material.length : (object.material ? 1 : 0);
      finite = finite && [object.scale.x, object.scale.y, object.scale.z, object.position.x, object.position.y, object.position.z].every(Number.isFinite);
      if (object.userData?.collider || object.name.toLowerCase().includes("collider")) colliderCount += 1;
    });
    result.animations = gltf.animations.length;
    result.checks = { scale: finite && result.meshes > 0 ? "pass" : "fail", material: result.materials >= result.meshes && result.materials > 0 ? "pass" : "fail", animation: result.animations >= ${expectedAnimations} ? "pass" : "fail", collider: colliderCount >= ${expectedColliders} ? "pass" : "fail" };
    scene.add(gltf.scene); renderer.render(scene, camera); window.__loaderResult = result;
  }, undefined, (error) => { result.error = String(error); window.__loaderResult = result; });
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
    raw.browser = { product: browser.version(), executable: browserExecutable, headed: false, viewport: { width: 320, height: 240 }, device_scale_factor: 1, screenshot_sha256: sha256(screenshot) };
    raw.source = "live-browser";
  } finally {
    await browser?.close().catch(() => {});
    await new Promise(resolveClose => server.close(resolveClose));
  }
  if (!raw || typeof raw !== "object") throw new Error("package browser probe produced no result");
  const expectedChecks = { scale: "pass", material: "pass", animation: "pass", collider: "pass" };
  const valid = raw.source === "live-browser" && raw.checks && Object.keys(expectedChecks).every(key => raw.checks[key] === "pass");
  const evidence = { schema_version: "1.0.0", kind: "gltf-loader-evidence", id: `${jobId}-gltf-loader`, artifact_commit: artifactCommit, glb_hash: glbHash, loader: { name: "three", version: String(raw.three_revision || "unknown"), entrypoint: "GLTFLoader" }, checks: expectedChecks, source: "live-browser", target_workspace: workspace, target_three_root: { path: threeRelative, three_module_sha256: sha256(threeBytes), gltf_loader_sha256: sha256(loaderBytes) }, browser: raw.browser, observed: { meshes: raw.meshes, materials: raw.materials, animations: raw.animations }, raw_probe_result: raw };
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
