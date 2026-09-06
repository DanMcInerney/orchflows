/**
 * Evidence admission is identity based. It re-hashes referenced bytes and
 * recomputes performance/session facts; a stored `passed: true` never becomes
 * acceptance evidence by itself.
 */
import { readFile, stat } from "node:fs/promises";
import { readFileSync } from "node:fs";
import { execFile as execFileCallback } from "node:child_process";
import { resolve, relative, isAbsolute, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import Ajv from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { parseArgs, readJson, resultFromError, sha256, inputError, evidenceError, ensureContained, requireObject, nowIso, writeJsonAtomic, canonicalJson } from "./_common.mjs";
import { qualifyPerformance } from "./trace_frames.mjs";
import { validateCommand } from "./browser_harness.mjs";
import { validateGateLineage, LineageError } from "./gate_lineage.mjs";

const execFile = promisify(execFileCallback);

const HEADER_KEYS = ["schema_version", "kind", "id", "artifact_commit", "created_at", "producer", "inputs", "environment", "status", "gaps", "invalidates"];

// These identities are the frozen acceptance surface from the approved
// workflow specification and rubrics.  A caller cannot replace one with a
// convenient alias or lower a critical dimension's floor.
export const CORE_HARD_GATE_IDS = Object.freeze([
  "production-boot",
  "focus-controls",
  "fundamental-loop",
  "central-mechanics-state-transitions",
  "core-progression-content-paths",
  "terminal-continuing-behavior",
  "replay-reentry",
  "readable-feedback-camera-collision",
  "no-undisclosed-placeholder",
  "complete-core-captures",
  "qualified-representative-performance",
]);
export const FINAL_HARD_GATE_IDS = Object.freeze([
  "clean-production-boot",
  "documented-controls-focus",
  "all-prompt-concept-promises",
  "mechanics-content-progression",
  "terminal-continuing-behavior",
  "replay-reentry",
  "no-blocking-errors-placeholders",
  "asset-provenance-disposal",
  "complete-capture-adaptive-play",
  "performance-cell-coverage",
]);
export const CORE_DIMENSION_IDS = Object.freeze([
  "loop-purpose-clarity",
  "controls-camera-feel",
  "interaction-feedback-readability",
  "fairness-challenge",
  "meaningful-choice-progression",
  "pacing-continued-engagement",
  "prompt-fidelity",
  "stability",
]);
export const FINAL_DIMENSION_IDS = Object.freeze([
  "prompt-fidelity",
  "loop-purpose",
  "controls-camera",
  "feedback-readability-fairness",
  "challenge-choice-pacing-engagement",
  "level-world-coherence",
  "3d-art-animation-motion-coherence",
  "promised-ui-audio-accessibility",
  "stability",
  "polish",
]);
const CRITICAL_SCORE_FLOOR = 3;

// Stored evidence is admitted through the package schemas as well as the
// semantic checks below.  The schemas are loaded from this package, so a
// caller cannot silently replace them with a schema from its evidence folder.
const REFERENCE_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../references");
const schemaJson = name => JSON.parse(readFileSync(resolve(REFERENCE_DIR, name), "utf8"));
const schemaValidator = (() => {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  const common = schemaJson("common.schema.json");
  ajv.addSchema(common);
  const lineage = schemaJson("lineage.schema.json");
  ajv.addSchema(lineage);
  const runRecord = ajv.compile(schemaJson("run-record.schema.json"));
  const traceability = ajv.compile(schemaJson("traceability.schema.json"));
  const play = ajv.compile(schemaJson("play-session.schema.json"));
  const performanceCell = ajv.compile(schemaJson("performance-cell.schema.json"));
  const performancePlan = ajv.compile(schemaJson("performance-plan.schema.json"));
  const evidenceIndex = ajv.compile(schemaJson("evidence-index.schema.json"));
  const gateVerdict = ajv.compile(schemaJson("gate-verdict.schema.json"));
  const captureMatrix = ajv.compile(schemaJson("capture-matrix.schema.json"));
  const assetManifest = ajv.compile(schemaJson("asset-manifest.schema.json"));
  return { runRecord, traceability, play, performanceCell, performancePlan, evidenceIndex, gateVerdict, captureMatrix, assetManifest };
})();

function validateStoredSchema(document, validator, label, pointer = "/") {
  if (validator(document)) return document;
  const details = (validator.errors || []).map(item => `${item.instancePath || "/"} ${item.message}`).join("; ");
  throw evidenceError(`${label} does not satisfy its package schema: ${details}`, pointer);
}

function requireHeader(document, expectedKind, pointer = "/") {
  requireObject(document, pointer);
  for (const key of HEADER_KEYS) if (!(key in document)) throw evidenceError(`missing header field ${key}`, `${pointer}/${key}`);
  if (document.kind !== expectedKind) throw evidenceError(`expected kind ${expectedKind}, observed ${document.kind}`, `${pointer}/kind`);
  if (typeof document.artifact_commit !== "string" || !document.artifact_commit) throw evidenceError("artifact_commit must be a non-empty identity", `${pointer}/artifact_commit`);
  if (!Array.isArray(document.gaps) || !Array.isArray(document.invalidates)) throw evidenceError("gaps and invalidates must be arrays", pointer);
  if (!Array.isArray(document.inputs) || document.inputs.some(item => !item || typeof item.name !== "string" || !/^sha256:[0-9a-f]{64}$/.test(item.sha256))) throw evidenceError("inputs must be named sha256 identities", `${pointer}/inputs`);
  if (!document.producer || typeof document.producer !== "object" || typeof document.producer.name !== "string") throw evidenceError("producer must be an object with name", `${pointer}/producer`);
  if (!document.environment || typeof document.environment !== "object" || typeof document.environment.host !== "string" || typeof document.environment.os !== "string" || !Array.isArray(document.environment.tools)) throw evidenceError("environment must include host, os, and tools", `${pointer}/environment`);
  return document;
}

function relativeSafe(baseDir, path, pointer) {
  if (typeof path !== "string" || !path || isAbsolute(path)) throw evidenceError("evidence path must be relative", pointer);
  const target = ensureContained(baseDir, resolve(baseDir, path), pointer);
  return { target, path: relative(resolve(baseDir), target).replaceAll("\\", "/") };
}

async function hashPath(baseDir, path, pointer) {
  const { target, path: normalized } = relativeSafe(baseDir, path, pointer);
  let bytes;
  try { bytes = await readFile(target); } catch (error) { throw evidenceError(`evidence file is missing: ${error.message}`, pointer); }
  return { target, path: normalized, hash: sha256(bytes), bytes };
}

async function hashContainedFile(rootDir, path, pointer) {
  if (typeof rootDir !== "string" || !rootDir || !isAbsolute(rootDir)) throw evidenceError("target workspace must be an absolute path", pointer);
  if (typeof path !== "string" || !path || isAbsolute(path)) throw evidenceError("target evidence path must be relative", pointer);
  const root = resolve(rootDir);
  const target = ensureContained(root, resolve(root, path));
  let bytes;
  try { bytes = await readFile(target); } catch (error) { throw evidenceError(`target evidence file is missing: ${error.message}`, pointer); }
  return { target, path: relative(root, target).replaceAll("\\", "/"), hash: sha256(bytes), bytes };
}

async function resolveContainedDirectory(rootDir, path, pointer) {
  if (typeof rootDir !== "string" || !rootDir || !isAbsolute(rootDir)) throw evidenceError("target workspace must be an absolute path", pointer);
  if (typeof path !== "string" || !path || isAbsolute(path)) throw evidenceError("target evidence path must be relative", pointer);
  const root = resolve(rootDir);
  const target = ensureContained(root, resolve(root, path));
  try {
    if (!(await stat(target)).isDirectory()) throw new Error("path is not a directory");
  } catch (error) { throw evidenceError(`target evidence directory is missing: ${error.message}`, pointer); }
  return { target, path: relative(root, target).replaceAll("\\", "/") };
}

function parsedTime(value, pointer) {
  if (typeof value !== "string" || !value || !Number.isFinite(Date.parse(value))) throw evidenceError("timestamp must be an ISO date-time", pointer);
  return Date.parse(value);
}

function meaningfulSnapshot(snapshot, pointer) {
  if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot)) throw evidenceError("successful observation needs a rendered snapshot", pointer);
  if (typeof snapshot.url !== "string" || !snapshot.url || !Array.isArray(snapshot.canvases) || !Number.isInteger(snapshot.canvas_count) || snapshot.canvas_count < 1) {
    throw evidenceError("rendered snapshot must include url, canvas_count, and canvases", pointer);
  }
  if (!snapshot.canvases.some(canvas => canvas && canvas.connected !== false && Number(canvas.width) > 0 && Number(canvas.height) > 0)) throw evidenceError("rendered snapshot has no usable connected canvas", pointer);
  return snapshot;
}

function sessionClassification(session) {
  const transcript = session.transcript;
  if (!Array.isArray(transcript)) throw evidenceError("play session transcript must be an array", "/transcript");
  const allowed = new Set(["observe", "key", "pointer", "wait", "capture", "stop"]);
  let previousSequence = 0;
  let previousMonotonic = -Infinity;
  let previousWall = -Infinity;
  let stopped = false;
  const observations = [];
  const actions = [];
  for (let index = 0; index < transcript.length; index += 1) {
    const item = transcript[index];
    if (!item || typeof item !== "object" || !item.command) throw evidenceError("transcript item lacks command", `/transcript/${index}`);
    const command = item.command;
    try { validateCommand(command); } catch (error) { throw evidenceError(`invalid ordinary-input command: ${error.message}`, `/transcript/${index}/command`); }
    if (!allowed.has(command.type)) throw evidenceError(`unsupported transcript command ${command.type}`, `/transcript/${index}/command/type`);
    const reply = item.reply;
    if (!reply || typeof reply !== "object" || Array.isArray(reply) || !Number.isInteger(reply.sequence) || reply.sequence <= previousSequence) throw evidenceError("every transcript command needs a strictly increasing reply sequence", `/transcript/${index}/reply/sequence`);
    if (reply.type !== command.type) throw evidenceError("reply type must match its ordinary-input command", `/transcript/${index}/reply/type`);
    if (reply.status !== "ok") throw evidenceError("play evidence cannot contain failed or unlabeled command replies", `/transcript/${index}/reply/status`);
    if (!Number.isFinite(reply.monotonic_ms) || reply.monotonic_ms < 0) throw evidenceError("reply needs a non-negative monotonic timestamp", `/transcript/${index}/reply/monotonic_ms`);
    const wall = parsedTime(reply.wall_time, `/transcript/${index}/reply/wall_time`);
    if (reply.monotonic_ms < previousMonotonic || wall < previousWall) throw evidenceError("transcript timestamps must be causally ordered", `/transcript/${index}/reply`);
    meaningfulSnapshot(reply.snapshot, `/transcript/${index}/reply/snapshot`);
    if (command.type === "capture" && typeof reply.screenshot_hash !== "string") throw evidenceError("capture reply needs its observed screenshot hash", `/transcript/${index}/reply/screenshot_hash`);
    if (command.type === "observe") observations.push({ index, sequence: reply.sequence });
    if (["key", "pointer"].includes(command.type)) actions.push({ index, sequence: reply.sequence });
    if (command.type === "stop") stopped = true;
    previousSequence = reply.sequence;
    previousMonotonic = reply.monotonic_ms;
    previousWall = wall;
  }
  if (!transcript.length || !stopped || transcript.at(-1).command.type !== "stop") throw evidenceError("play session must end with an observed stop command", "/transcript");
  const requested = session.classification || session.input_mode;
  if (!["actual_play", "scripted_input", "simulated"].includes(requested)) throw evidenceError(`invalid play classification ${requested}`, "/classification");
  const started = parsedTime(session.started_at, "/started_at");
  const ended = parsedTime(session.ended_at, "/ended_at");
  if (ended <= started) throw evidenceError("play session ended before it started", "/ended_at");
  if (session.input_mode !== undefined && session.input_mode !== requested) throw evidenceError("classification and input_mode disagree", "/input_mode");
  if (requested === "actual_play") {
    if (typeof session.operator !== "string" || !session.operator.trim() || typeof session.independent_context_id !== "string" || !session.independent_context_id.trim()) throw evidenceError("actual play requires operator and independent_context_id", "/classification");
    if (session.source !== "live-browser") throw evidenceError("actual play requires a live-browser session source", "/source");
    if (session.headed !== true) throw evidenceError("actual play requires headed evidence", "/headed");
    if (!session.environment?.browser || !session.environment?.browser_version || session.environment.browser_version === "unknown" || !session.environment?.driver) throw evidenceError("actual play requires browser name, version, and driver identity", "/environment");
    const firstAction = actions[0];
    const before = firstAction && observations.find(item => item.index < firstAction.index);
    const after = firstAction && observations.find(item => item.index > firstAction.index);
    if (!firstAction || !before || !after) throw evidenceError("actual play requires a successful fresh observation, ordinary action, and subsequent observation", "/transcript");
    const adaptation = session.adaptation;
    if (!adaptation || typeof adaptation !== "object" || Array.isArray(adaptation) || typeof adaptation.rationale !== "string" || !adaptation.rationale.trim()) throw evidenceError("actual play requires a recorded adaptation rationale", "/adaptation");
    if (adaptation.observation_sequence !== before.sequence || adaptation.action_sequence !== firstAction.sequence || adaptation.subsequent_observation_sequence !== after.sequence) throw evidenceError("adaptation facts do not match the causal transcript order", "/adaptation");
    return { requested, observations: observations.length, adapted: true, adaptation: { observation_sequence: before.sequence, action_sequence: firstAction.sequence, subsequent_observation_sequence: after.sequence, rationale: adaptation.rationale } };
  }
  return { requested, observations: observations.length, adapted: false };
}

export function validatePlaySession(session) {
  requireHeader(session, "play-session");
  validateStoredSchema(session, schemaValidator.play, "play session");
  const facts = sessionClassification(session);
  if (session.transcript_hash !== sha256(canonicalTranscript(session.transcript))) throw evidenceError("transcript_hash does not match immutable transcript bytes", "/transcript_hash");
  if (session.status === "pass" || session.status === "qualified") throw evidenceError("a play session cannot promote itself to a gate verdict", "/status");
  return { status: "valid", ...facts };
}

function canonicalTranscript(transcript) {
  return `${JSON.stringify(transcript, (_key, item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    return Object.keys(item).sort().reduce((out, key) => { out[key] = item[key]; return out; }, {});
  }, 2)}\n`;
}

function resultIdentity(value) {
  if (typeof value !== "string" || !/^sha256:[0-9a-f]{64}$/i.test(value)) throw evidenceError("expected a sha256 identity", "/hash");
}

export async function validatePerformanceCell(document) {
  requireHeader(document, "performance-cell");
  validateStoredSchema(document, schemaValidator.performanceCell, "performance cell");
  if (!document.cell || !document.trace || !Array.isArray(document.callbacks)) throw evidenceError("performance result must preserve cell, trace, and callback samples", "/");
  if (!["live-browser", "qualification-fixture"].includes(document.source)) throw evidenceError("performance result must declare live-browser or qualification-fixture source", "/source");
  if (document.cell.artifact_commit !== document.artifact_commit) throw evidenceError("performance cell and result are bound to different artifact commits", "/cell/artifact_commit");
  const measurement = document.measurement;
  if (document.source === "live-browser" && (!measurement || typeof measurement !== "object" || measurement.scenario_id !== document.cell.scenario_id || !measurement.warmup || !measurement.control || !measurement.instrumented || !measurement.perturbation)) throw evidenceError("live performance result must preserve the measured scenario and warm-up/control/instrumented phases", "/measurement");
  const window = document.cell.window;
  if (document.source === "live-browser" && (!window || !Number.isFinite(window.start_ms) || !Number.isFinite(window.end_ms) || window.end_ms <= window.start_ms)) throw evidenceError("live performance result must preserve a positive measured window", "/cell/window");
  const qualification = qualifyPerformance({ cell: document.cell, trace: document.trace, callbacks: document.callbacks });
  if (qualification.status !== "qualified") throw evidenceError("performance: unverified", "/qualification");
  if (!document.qualification || document.qualification.status !== qualification.status) throw evidenceError("stored performance qualification does not match recomputed result", "/qualification/status");
  return { status: "valid", qualification };
}

async function readEvidenceJson(baseDir, path, expectedHash, pointer, label) {
  if (typeof path !== "string" || !path || typeof expectedHash !== "string") throw evidenceError(`${label} must name a relative, hashed JSON report`, pointer);
  resultIdentity(expectedHash);
  const observed = await hashPath(baseDir, path, `${pointer}/path`);
  if (observed.hash !== expectedHash) throw evidenceError(`${label} hash does not match its bytes`, `${pointer}/sha256`);
  let value;
  try { value = JSON.parse(observed.bytes.toString("utf8")); } catch (error) { throw evidenceError(`${label} is not valid JSON: ${error.message}`, `${pointer}/path`); }
  if (!value || typeof value !== "object" || Array.isArray(value)) throw evidenceError(`${label} must contain a JSON object`, `${pointer}/path`);
  return { value, observed };
}

async function runPinnedKhronosValidator(bytes, pointer) {
  let imported;
  try { imported = await import("gltf-validator"); } catch (error) { throw evidenceError(`pinned glTF Validator is unavailable: ${error.message}`, pointer); }
  const validator = imported.default?.validateBytes ? imported.default : imported;
  if (typeof validator.validateBytes !== "function") throw evidenceError("pinned glTF Validator has no validateBytes API", pointer);
  let report;
  try { report = await validator.validateBytes(new Uint8Array(bytes), { format: "glb", maxIssues: 0, writeTimestamp: false }); } catch (error) { throw evidenceError(`pinned Khronos validation failed to run: ${error.message}`, pointer); }
  const errors = report?.issues?.numErrors;
  if (!Number.isInteger(errors)) throw evidenceError("pinned Khronos report did not contain issues.numErrors", pointer);
  if (errors !== 0) throw evidenceError(`pinned Khronos validation reported ${errors} errors`, pointer);
  return report;
}

export async function validateAssetManifest(manifest, { baseDir = process.cwd() } = {}) {
  requireHeader(manifest, "asset-manifest");
  validateStoredSchema(manifest, schemaValidator.assetManifest, "asset manifest");
  const glbPath = manifest.runtime_glb;
  const expectedHash = manifest.exported_glb_sha256;
  if (!glbPath || !expectedHash) throw evidenceError("asset manifest needs runtime_glb and exported_glb_sha256", "/runtime_glb");
  resultIdentity(expectedHash);
  const observed = await hashPath(baseDir, glbPath, "/runtime_glb");
  if (observed.hash !== expectedHash) throw evidenceError(`GLB hash mismatch: expected ${expectedHash}, observed ${observed.hash}`, "/exported_glb_sha256");
  const validation = manifest.validation;
  const khronos = validation?.khronos;
  const loader = validation?.gltf_loader;
  if (!validation || !khronos || khronos.status !== "pass" || Number(khronos.errors) !== 0 || khronos.export_sha256 !== expectedHash) throw evidenceError("pinned Khronos validation is missing, failed, or bound to another GLB", "/validation/khronos");
  const khronosEvidence = await readEvidenceJson(baseDir, khronos.report_path, khronos.report_sha256, "/validation/khronos", "Khronos report");
  if (!Number.isInteger(khronosEvidence.value?.issues?.numErrors) || khronosEvidence.value.issues.numErrors !== 0) throw evidenceError("Khronos report does not prove zero validation errors", "/validation/khronos/report_path");
  if (khronosEvidence.value.orchflows?.kind !== "khronos-validation" || khronosEvidence.value.orchflows?.source !== "package-owned-fresh-process" || khronosEvidence.value.orchflows?.artifact_commit !== manifest.artifact_commit || khronosEvidence.value.orchflows?.glb_hash !== expectedHash) throw evidenceError("Khronos report is not a fresh package-owned observation of this artifact and GLB", "/validation/khronos/report_path");
  await runPinnedKhronosValidator(observed.bytes, "/validation/khronos");
  if (!loader || loader.status !== "pass" || !loader.evidence_id || !loader.artifact_commit || loader.artifact_commit !== manifest.artifact_commit || loader.glb_hash !== expectedHash) throw evidenceError("target GLTFLoader proof is missing, not passed, or bound to another GLB/artifact", "/validation/gltf_loader");
  const loaderEvidence = await readEvidenceJson(baseDir, loader.evidence_path, loader.evidence_sha256, "/validation/gltf_loader", "GLTFLoader evidence");
  const loaderDocument = loaderEvidence.value;
  if (loaderDocument.kind !== "gltf-loader-evidence" || loaderDocument.source !== "live-browser" || loaderDocument.id !== loader.evidence_id || loaderDocument.artifact_commit !== manifest.artifact_commit || loaderDocument.glb_hash !== expectedHash || typeof loaderDocument.target_workspace !== "string" || !loaderDocument.target_workspace || !loaderDocument.target_probe?.path || !/^sha256:[0-9a-f]{64}$/i.test(loaderDocument.target_probe?.sha256 || "")) throw evidenceError("GLTFLoader evidence identity is not bound to this artifact, exact GLB, and target browser probe", "/validation/gltf_loader/evidence_path");
  const targetProbe = await hashContainedFile(dirname(loaderEvidence.observed.target), loaderDocument.target_probe.path, "/validation/gltf_loader/target_probe/path");
  if (targetProbe.hash !== loaderDocument.target_probe.sha256 || loaderDocument.browser?.screenshot_sha256 !== targetProbe.hash) throw evidenceError("GLTFLoader evidence screenshot hash does not match retained browser bytes", "/validation/gltf_loader/target_probe/sha256");
  const targetRoot = loaderDocument.target_three_root;
  if (!targetRoot || typeof targetRoot.path !== "string" || !/^sha256:[0-9a-f]{64}$/i.test(targetRoot.three_module_sha256 || "") || !/^sha256:[0-9a-f]{64}$/i.test(targetRoot.gltf_loader_sha256 || "")) throw evidenceError("GLTFLoader evidence lacks hash-bound target Three.js module identities", "/validation/gltf_loader/evidence_path");
  const threeRoot = await resolveContainedDirectory(loaderDocument.target_workspace, targetRoot.path, "/validation/gltf_loader/target_three_root/path");
  const threeModule = await hashContainedFile(threeRoot.target, "build/three.module.js", "/validation/gltf_loader/target_three_root/three_module_sha256");
  const loaderModule = await hashContainedFile(threeRoot.target, "examples/jsm/loaders/GLTFLoader.js", "/validation/gltf_loader/target_three_root/gltf_loader_sha256");
  if (threeModule.hash !== targetRoot.three_module_sha256 || loaderModule.hash !== targetRoot.gltf_loader_sha256) throw evidenceError("GLTFLoader evidence target module hashes do not match current target bytes", "/validation/gltf_loader/target_three_root");
  const observedAsset = loaderDocument.observed;
  if (!observedAsset || !Number.isInteger(observedAsset.meshes) || observedAsset.meshes < 1 || !Number.isInteger(observedAsset.materials) || observedAsset.materials < observedAsset.meshes || !Number.isInteger(observedAsset.animations) || observedAsset.animations < 0) throw evidenceError("GLTFLoader evidence lacks measured scene inspection counts", "/validation/gltf_loader/evidence_path");
  const checks = loader.checks || {};
  for (const key of ["scale", "material", "animation", "collider"]) if (checks[key] !== "pass") throw evidenceError(`GLTFLoader proof ${key} check is not passed`, `/validation/gltf_loader/checks/${key}`);
  const observedChecks = loaderEvidence.value.checks;
  for (const key of ["scale", "material", "animation", "collider"]) if (observedChecks?.[key] !== "pass") throw evidenceError(`GLTFLoader evidence ${key} check is not passed`, `/validation/gltf_loader/evidence_path`);
  return { status: "valid", glb: { path: observed.path, hash: observed.hash }, khronos_errors: 0, gltf_loader: loader.evidence_id };
}

async function validateCapture(document, { baseDir = process.cwd() } = {}) {
  requireHeader(document, "capture");
  const capture = document.capture || document.screenshot || {};
  if (!capture.path || !capture.hash) throw evidenceError("capture evidence needs a relative screenshot path and hash", "/capture");
  resultIdentity(capture.hash);
  const observed = await hashPath(baseDir, capture.path, "/capture/path");
  if (observed.hash !== capture.hash) throw evidenceError("capture screenshot hash mismatch", "/capture/hash");
  if (!document.viewport || !Number.isInteger(document.viewport.width) || document.viewport.width < 1 || !Number.isInteger(document.viewport.height) || document.viewport.height < 1 || !Number.isFinite(document.dpr) || document.dpr <= 0 || document.state === undefined || document.state === null || document.state === "") throw evidenceError("capture lacks a valid viewport, DPR, or state binding", "/capture");
  return { status: "valid" };
}

function validateCaptureMatrix(document) {
  requireHeader(document, "capture-matrix");
  if (!Array.isArray(document.cells) || document.cells.length === 0) throw evidenceError("capture matrix has no cells", "/cells");
  const ids = new Set();
  for (const cell of document.cells) {
    if (!cell || typeof cell.id !== "string" || ids.has(cell.id)) throw evidenceError("capture matrix cells need unique ids", "/cells");
    if (typeof cell.state !== "string" || !cell.state || !cell.viewport || !Number.isInteger(cell.viewport.width) || cell.viewport.width < 1 || !Number.isInteger(cell.viewport.height) || cell.viewport.height < 1 || !Number.isFinite(cell.dpr) || cell.dpr <= 0) throw evidenceError(`capture matrix cell ${cell.id} lacks a valid state, viewport, and DPR`, "/cells");
    ids.add(cell.id);
    if (cell.required !== false && (!Array.isArray(cell.capture_ids) || cell.capture_ids.length === 0) && document.status === "complete") throw evidenceError(`required capture cell ${cell.id} is missing capture evidence`, `/cells/${cell.id}`);
  }
  return { status: "valid", cells: document.cells.length };
}

function validatePerformancePlan(document) {
  requireHeader(document, "performance-plan");
  validateStoredSchema(document, schemaValidator.performancePlan, "performance plan");
  const groups = document.groups || document.scenarios;
  if (!Array.isArray(groups) || groups.length === 0) throw evidenceError("performance plan needs at least one scenario group", "/groups");
  const seen = new Set();
  const normalized = groups.map((group, index) => {
    if (!group || typeof group !== "object" || Array.isArray(group)) throw evidenceError("performance plan scenario must be an object", `/groups/${index}`);
    const id = group.id || group.scenario || group.scenario_id || group.name;
    if (typeof id !== "string" || !id || seen.has(id)) throw evidenceError("performance plan scenarios need unique ids", `/groups/${index}/id`);
    seen.add(id);
    const animated = group.animated !== false;
    const requiredRuns = group.required_runs ?? group.runs ?? (animated ? 3 : 1);
    const minDuration = group.min_duration_seconds ?? group.duration_seconds ?? (animated ? 60 : 0);
    if (!Number.isInteger(requiredRuns) || requiredRuns < (animated ? 3 : 1)) throw evidenceError("animated performance scenarios require at least three runs", `/groups/${index}/required_runs`);
    if (!Number.isFinite(minDuration) || minDuration < (animated ? 60 : 0)) throw evidenceError("animated performance scenarios require a 60-second minimum duration", `/groups/${index}/min_duration_seconds`);
    const cells = group.cells || group.cell_ids || [];
    if (!Array.isArray(cells)) throw evidenceError("performance plan scenario cells must be an array", `/groups/${index}/cells`);
    const cellIds = cells.map(cell => typeof cell === "string" ? cell : cell?.id || cell?.cell_id);
    if (cellIds.some(cell => typeof cell !== "string" || !cell)) throw evidenceError("performance plan scenario cells need identities", `/groups/${index}/cells`);
    if (new Set(cellIds).size !== cellIds.length) throw evidenceError("performance plan scenario cells need unique identities", `/groups/${index}/cells`);
    return { id, animated, required_runs: requiredRuns, min_duration_seconds: minDuration, cell_ids: cellIds };
  });
  return { status: "valid", scenarios: normalized };
}

function performanceRunId(item) {
  const cell = item.document?.cell || {};
  const value = item.document?.run_id || item.document?.run || cell.run_id || cell.run || cell.attempt_id || cell.attempt || item.document?.id;
  return typeof value === "string" && value ? value : null;
}

function performanceScenario(item) {
  const cell = item.document?.cell || {};
  return item.document?.scenario || cell.scenario || cell.scenario_id || null;
}

function performanceCellId(item) {
  return item.document?.cell?.id || item.document?.id || item.id;
}

function performanceWarm(item) {
  const cell = item.document?.cell;
  const measurement = item.document?.measurement;
  const warmup = measurement?.warmup;
  if (!cell || !measurement || measurement.scenario_id !== cell.scenario_id || !warmup || warmup.status !== "observed") return false;
  const requested = Number(warmup.requested_ms);
  const observed = Number(warmup.observed_ms);
  return Number.isFinite(requested) && requested > 0 && Number.isFinite(observed) && observed >= requested;
}

function performanceDuration(item) {
  const cell = item.document?.cell || {};
  const duration = cell.duration_seconds ?? ((cell.window?.end_ms - cell.window?.start_ms) / 1000);
  return Number(duration);
}

function performanceConfiguration(item) {
  const cell = item.document?.cell || {};
  const excluded = new Set(["id", "run_id", "run", "attempt", "attempt_id", "warmup", "warmup_index", "warm", "warmup_complete", "warmup_completed", "warmup_seconds", "warmup_duration_seconds", "window"]);
  return canonicalJson(Object.fromEntries(Object.entries(cell).filter(([key]) => !excluded.has(key))));
}

function validatePerformanceCoverage(planFacts, performanceEntries, pointer) {
  const assigned = new Set();
  const coverage = [];
  for (const scenario of planFacts.scenarios) {
    const plannedCells = new Set(scenario.cell_ids);
    const candidates = performanceEntries.filter(item => {
      const scenarioMatch = performanceScenario(item) === scenario.id || (!performanceScenario(item) && plannedCells.has(performanceCellId(item)));
      const cellMatch = plannedCells.size === 0 || plannedCells.has(performanceCellId(item));
      return scenarioMatch && cellMatch;
    });
    const scopes = plannedCells.size ? [...plannedCells].map(cellId => ({ id: cellId, entries: candidates.filter(item => performanceCellId(item) === cellId) })) : [{ id: scenario.id, entries: candidates }];
    for (const scope of scopes) {
      if (scope.entries.length < scenario.required_runs) throw evidenceError(`performance plan scenario ${scenario.id} cell ${scope.id} lacks required runs`, pointer);
      const runs = new Set();
      for (const item of scope.entries) {
        assigned.add(item.id);
        const run = performanceRunId(item);
        if (!run) throw evidenceError(`performance scenario ${scenario.id} has a run without a stable run identity`, pointer);
        runs.add(run);
        if (!performanceWarm(item)) throw evidenceError(`performance scenario ${scenario.id} has a run without completed warm-up evidence`, pointer);
        if (performanceDuration(item) < scenario.min_duration_seconds) throw evidenceError(`performance scenario ${scenario.id} has a run shorter than its frozen duration`, pointer);
      }
      if (runs.size < scenario.required_runs) throw evidenceError(`performance plan scenario ${scenario.id} cell ${scope.id} lacks distinct runs`, pointer);
      if (new Set(scope.entries.map(performanceConfiguration)).size !== 1) throw evidenceError(`performance scenario ${scenario.id} runs do not share one frozen configuration`, pointer);
      const selected = scope.entries.filter(item => [...runs].indexOf(performanceRunId(item)) < scenario.required_runs);
      coverage.push({ scenario: scenario.id, cell: scope.id, runs: [...runs].sort(), evidence_ids: selected.map(item => item.id).sort() });
    }
  }
  if (assigned.size !== performanceEntries.length) throw evidenceError("performance evidence includes an unplanned scenario or cell", pointer);
  return coverage;
}

async function loadEntry(baseDir, entry, index) {
  if (!entry || typeof entry !== "object") throw evidenceError("evidence entry must be an object", "/entries");
  for (const key of ["kind", "path", "sha256", "revision"]) if (!(key in entry)) throw evidenceError(`entry missing ${key}`, "/entries");
  resultIdentity(entry.sha256);
  if (!["same-artifact", "declared-ancestor"].includes(entry.revision)) throw evidenceError(`invalid evidence revision ${entry.revision}`, "/entries/revision");
  const key = entry.id || entry.path;
  const observed = await hashPath(baseDir, entry.path, `/entries/${key}/path`);
  if (observed.hash !== entry.sha256) throw evidenceError(`evidence hash mismatch for ${key}`, `/entries/${key}/sha256`);
  let document = null;
  try { document = JSON.parse(observed.bytes.toString("utf8")); } catch { throw evidenceError(`evidence entry ${key} is not JSON`, `/entries/${key}/path`); }
  const identity = document.id || key;
  if (entry.id && entry.id !== identity) throw evidenceError(`entry id ${entry.id} does not match document id ${identity}`, `/entries/${key}/id`);
  if (document.artifact_commit) {
    const ancestors = index.declared_ancestors || index.ancestors || [];
    if (entry.revision === "same-artifact" && document.artifact_commit !== index.artifact_commit) throw evidenceError(`entry ${identity} is not from the indexed artifact`, `/entries/${key}/revision`);
    if (entry.revision === "declared-ancestor" && !ancestors.includes(document.artifact_commit)) throw evidenceError(`entry ${identity} is from an undeclared artifact commit`, `/entries/${key}/source_commit`);
  }
  let facts = { status: "valid" };
  if (document.kind === "run-record") { validateStoredSchema(document, schemaValidator.runRecord, "run record"); facts = { status: "schema-valid", kind: document.kind }; }
  if (document.kind === "traceability") { validateStoredSchema(document, schemaValidator.traceability, "traceability"); facts = { status: "schema-valid", kind: document.kind }; }
  if (document.kind === "gate-verdict") { validateStoredSchema(document, schemaValidator.gateVerdict, "gate verdict"); facts = { status: "schema-valid", kind: document.kind }; }
  if (document.kind === "play-session" || entry.kind === "play-session") facts = validatePlaySession(document);
  if (document.kind === "performance-cell" || entry.kind === "performance") facts = await validatePerformanceCell(document);
  if (document.kind === "asset-manifest" || entry.kind === "manifest" || entry.kind === "asset") facts = await validateAssetManifest(document, { baseDir: dirname(observed.target) });
  if (document.kind === "capture" || entry.kind === "capture") facts = await validateCapture(document, { baseDir: dirname(observed.target) });
  if (document.kind === "capture-matrix") {
    validateStoredSchema(document, schemaValidator.captureMatrix, "capture matrix");
    facts = validateCaptureMatrix(document);
  }
  if (document.kind === "performance-plan" || entry.kind === "performance-plan") facts = validatePerformancePlan(document);
  return { entry, document, observed, id: identity, facts };
}

function validationReceipt(index, loaded, required, kinds) {
  return {
    version: "1.0.0",
    kind: "evidence-index-validation",
    index_id: index.id,
    artifact_commit: index.artifact_commit,
    entries: loaded.map(item => ({
      id: item.id,
      kind: item.entry.kind,
      path: item.observed.path,
      sha256: item.observed.hash,
      revision: item.entry.revision,
      document_kind: item.document.kind || null,
      facts: item.facts,
    })).sort((left, right) => left.id.localeCompare(right.id)),
    required: required.map(item => typeof item === "string" ? { id: item } : { id: item.id, ...(item.kind ? { kind: item.kind } : {}) }).sort((left, right) => left.id.localeCompare(right.id)),
    required_kinds: [...kinds.entries()].map(([kind, count]) => ({ kind, count })).sort((left, right) => left.kind.localeCompare(right.kind)),
  };
}

function documentFor(loaded, id, predicate = () => true, allowFallback = false) {
  if (typeof id === "string") {
    const exact = loaded.find(item => item.id === id && predicate(item.document, item));
    if (exact) return exact.document;
    return undefined;
  }
  if (!allowFallback) return undefined;
  return loaded.find(item => predicate(item.document, item))?.document;
}

function lineageEvidenceIndex(index, loaded) {
  return {
    ...index,
    entries: loaded.map(item => ({ ...item.entry, id: item.id, document: item.document })),
  };
}

async function observedGitAncestor(baseDir, ancestor, descendant) {
  const normalize = value => String(value).replace(/^git:/i, "");
  try {
    await execFile("git", ["-C", resolve(baseDir), "merge-base", "--is-ancestor", normalize(ancestor), normalize(descendant)], { timeout: 30000, windowsHide: true });
    return true;
  } catch (error) {
    if (Number(error?.code) === 1) return false;
    return undefined;
  }
}

function lineageInputs(index, gate, loaded, record, baseDir) {
  const fixed = record.fixed_inputs || {};
  const runRecord = documentFor(loaded, fixed.run_record, document => document?.kind === "run-record" && document.artifact_commit === index.artifact_commit);
  const traceability = documentFor(loaded, fixed.traceability, document => document?.kind === "traceability");
  const brief = documentFor(loaded, undefined, document => document?.kind === "brief" || document?.kind === "program-brief" || document?.promises || document?.promise_ids, true);
  const predecessorId = fixed.predecessor_run_record || runRecord?.lineage?.predecessor || runRecord?.predecessor;
  const predecessorRunRecord = predecessorId ? documentFor(loaded, predecessorId, document => document?.kind === "run-record") : undefined;
  const coreId = fixed.accepted_core_verdict || fixed.core_gate_verdict || fixed.core_verdict;
  const coreGateVerdict = gate === "final"
    ? documentFor(loaded, coreId, document => document?.kind === "gate-verdict" && document?.gate === "core")
    : undefined;
  const reproof = fixed.affected_core_reproof || fixed.core_reproof;
  const coreReproof = reproof && typeof reproof === "object"
    ? { ...reproof, verdict_record: documentFor(loaded, reproof.verdict, document => document?.kind === "gate-verdict" && document?.gate === "core") }
    : undefined;
  if (!runRecord) throw evidenceError("gate lineage requires an indexed typed run record", "/lineage/run_record");
  if (!traceability) throw evidenceError("gate lineage requires an indexed typed traceability record", "/lineage/traceability");
  if (!brief) throw evidenceError("gate lineage requires an indexed original brief record", "/lineage/brief");
  if (gate === "final" && !coreGateVerdict) throw evidenceError("final gate lineage requires its indexed accepted core verdict", "/lineage/core_gate_verdict");
  return {
    gate,
    runRecord,
    predecessorRunRecord,
    brief,
    amendments: runRecord.amendments || [],
    traceability,
    evidenceIndex: lineageEvidenceIndex(index, loaded),
    gateVerdict: record,
    coreGateVerdict,
    coreReproof,
    sourceObservation: (ancestor, descendant) => observedGitAncestor(baseDir, ancestor, descendant),
  };
}

export async function validateEvidenceIndex(index, { baseDir = process.cwd(), allowDraft = false } = {}) {
  requireHeader(index, "evidence-index");
  validateStoredSchema(index, schemaValidator.evidenceIndex, "evidence index");
  if (index.promotion && (index.promotion.validator !== "validate_evidence.mjs" || !/^sha256:[0-9a-f]{64}$/i.test(index.promotion.result_identity || ""))) throw evidenceError("evidence index promotion is not a validate_evidence.mjs result identity", "/promotion");
  if (!index.promotion && !(allowDraft && index.status === "draft")) throw evidenceError("evidence index is not promoted by validate_evidence.mjs", "/promotion");
  if (index.promotion && index.status !== "complete") throw evidenceError("a promoted evidence index must be complete", "/status");
  const entries = index.entries || index.evidence;
  if (!Array.isArray(entries)) throw evidenceError("evidence-index requires entries", "/entries");
  const ids = new Set();
  const paths = new Set();
  const loaded = [];
  for (const entry of entries) {
    const key = entry?.id || entry?.path;
    if (ids.has(key)) throw evidenceError(`duplicate evidence id ${key}`, "/entries");
    if (paths.has(entry.path)) throw evidenceError(`conflicting evidence path ${entry.path}`, "/entries");
    paths.add(entry.path);
    const loadedEntry = await loadEntry(baseDir, entry, index);
    ids.add(loadedEntry.id); loaded.push(loadedEntry);
  }
  const required = index.required || index.required_evidence || [];
  if (!Array.isArray(required)) throw evidenceError("required evidence must be an array", "/required");
  for (const requirement of required) {
    const id = typeof requirement === "string" ? requirement : requirement?.id;
    if (!id || !ids.has(id)) throw evidenceError(`required evidence is missing: ${id || JSON.stringify(requirement)}`, "/required");
    if (typeof requirement === "object" && requirement.kind && !loaded.find(item => item.id === id && (item.entry.kind === requirement.kind || item.document.kind === requirement.kind))) throw evidenceError(`required evidence ${id} has the wrong kind`, "/required");
  }
  const kinds = new Map();
  for (const item of loaded) kinds.set(item.entry.kind, (kinds.get(item.entry.kind) || 0) + 1);
  for (const requirement of index.required_kinds || []) {
    const count = kinds.get(requirement.kind) || 0;
    if (count < (requirement.count || 1)) throw evidenceError(`missing required evidence kind ${requirement.kind}`, "/required_kinds");
  }
  const requiredReceipt = index.required || index.required_evidence || [];
  const receipt = validationReceipt(index, loaded, requiredReceipt, kinds);
  const computedIdentity = sha256(canonicalJson(receipt));
  if (index.promotion && index.promotion.result_identity.toLowerCase() !== computedIdentity) throw evidenceError(`promotion result identity does not match the rehashed validation receipt; expected ${computedIdentity}, observed ${index.promotion.result_identity}`, "/promotion/result_identity");
  return { status: "valid", ids: [...ids], entries: loaded, kinds: Object.fromEntries(kinds), receipt, result_identity: computedIdentity };
}

export async function validateGate(index, gate, { baseDir = process.cwd() } = {}) {
  const evidence = await validateEvidenceIndex(index, { baseDir });
  const record = index.gates?.[gate] || evidence.entries.map(item => item.document).find(document => document.kind === "gate-verdict" && document.gate === gate);
  if (!record) throw evidenceError(`missing ${gate} gate record`, `/gates/${gate}`);
  validateStoredSchema(record, schemaValidator.gateVerdict, `${gate} gate verdict`);
  if (record.gate !== gate) throw evidenceError(`gate record is for ${record.gate}, not ${gate}`, `/gates/${gate}/gate`);
  if (record.artifact_commit && record.artifact_commit !== index.artifact_commit) throw evidenceError("gate record is bound to a different artifact commit", `/gates/${gate}/artifact_commit`);
  const requiredHard = [...(gate === "core" ? CORE_HARD_GATE_IDS : FINAL_HARD_GATE_IDS)];
  if (gate === "core" && record.fixed_inputs?.final_boss_promised === true) requiredHard.splice(7, 0, "functional-final-boss");
  const hardGates = record.hard_gates;
  if (!Array.isArray(hardGates) || hardGates.length !== requiredHard.length) throw evidenceError(`gate must enumerate exactly ${requiredHard.length} frozen hard gates`, `/gates/${gate}/hard_gates`);
  const hardIds = hardGates.map(item => item?.id);
  if (new Set(hardIds).size !== hardIds.length || requiredHard.some(id => !hardIds.includes(id)) || hardIds.some(id => !requiredHard.includes(id))) throw evidenceError("gate hard-gate identities do not match the frozen specification", `/gates/${gate}/hard_gates`);
  for (const hard of hardGates) {
    if (!hard || typeof hard !== "object" || !Array.isArray(hard.evidence) || hard.evidence.length === 0) throw evidenceError("each hard gate needs evidence identities; booleans cannot self-qualify", `/gates/${gate}/hard_gates`);
    if (hard.result !== "pass") throw evidenceError(`hard gate ${hard.id} is not passed`, `/gates/${gate}/hard_gates/${hard.id}`);
    for (const id of hard.evidence) {
      const item = evidence.entries.find(candidate => candidate.id === id);
      if (!item) throw evidenceError(`hard gate ${hard.id} references missing evidence ${id}`, `/gates/${gate}/hard_gates/${hard.id}`);
      if (item.entry.kind === "other" || !item.document.kind) throw evidenceError(`hard gate ${hard.id} references untyped evidence ${id}`, `/gates/${gate}/hard_gates/${hard.id}`);
    }
  }
  const dimensions = record.scores;
  const requiredDimensions = gate === "core" ? CORE_DIMENSION_IDS : FINAL_DIMENSION_IDS;
  if (!Array.isArray(dimensions) || dimensions.length !== requiredDimensions.length) throw evidenceError(`gate must score exactly ${requiredDimensions.length} frozen dimensions`, `/gates/${gate}/scores`);
  const dimensionIds = dimensions.map(item => item?.dimension);
  if (new Set(dimensionIds).size !== dimensionIds.length || requiredDimensions.some(id => !dimensionIds.includes(id)) || dimensionIds.some(id => !requiredDimensions.includes(id))) throw evidenceError("gate dimension identities do not match the frozen rubric", `/gates/${gate}/scores`);
  for (const dimension of dimensions) {
    if (!Number.isInteger(dimension.score) || dimension.score < 0 || dimension.score > 4 || dimension.score < CRITICAL_SCORE_FLOOR || (dimension.floor !== undefined && dimension.floor !== CRITICAL_SCORE_FLOOR)) throw evidenceError(`dimension ${dimension.dimension || "unknown"} is below the frozen floor of ${CRITICAL_SCORE_FLOOR}`, `/gates/${gate}/scores`);
    if (!Array.isArray(dimension.evidence) || dimension.evidence.length === 0 || dimension.evidence.some(id => {
      const item = evidence.entries.find(candidate => candidate.id === id);
      return !item || item.entry.kind === "other" || !item.document.kind;
    })) throw evidenceError(`dimension ${dimension.dimension} lacks bound typed evidence`, `/gates/${gate}/scores`);
  }
  const fixed = record.fixed_inputs || {};
  if (fixed.artifact_commit !== index.artifact_commit) throw evidenceError("gate fixed inputs are bound to a different artifact commit", `/gates/${gate}/fixed_inputs/artifact_commit`);
  if (fixed.evidence_index !== index.id) throw evidenceError("gate fixed inputs must name this promoted evidence index", `/gates/${gate}/fixed_inputs/evidence_index`);
  for (const key of ["traceability", "rubric_revision"]) {
    const item = typeof fixed[key] === "string" ? evidence.entries.find(candidate => candidate.id === fixed[key]) : null;
    if (!item || item.entry.kind === "other" || !item.document.kind || (key === "traceability" && item.document.kind !== "traceability")) throw evidenceError(`gate fixed input ${key} is not bound to typed evidence`, `/gates/${gate}/fixed_inputs/${key}`);
  }
  if (!Array.isArray(fixed.play_sessions) || fixed.play_sessions.length < 2 || new Set(fixed.play_sessions).size !== fixed.play_sessions.length) throw evidenceError("gate requires two independent play contexts", `/gates/${gate}/fixed_inputs/play_sessions`);
  const playEntries = fixed.play_sessions.map(id => evidence.entries.find(item => item.id === id));
  if (playEntries.some(item => !item)) throw evidenceError("gate references a missing play session", `/gates/${gate}/fixed_inputs/play_sessions`);
  if (playEntries.some(item => item.document.kind !== "play-session" || item.document.classification !== "actual_play" || item.document.source !== "live-browser" || item.document.headed !== true || typeof item.document.operator !== "string" || !item.document.operator || typeof item.document.independent_context_id !== "string" || !item.document.independent_context_id)) throw evidenceError("gate play coverage requires live headed actual-play provenance", `/gates/${gate}/fixed_inputs/play_sessions`);
  if (new Set(playEntries.map(item => item.document.independent_context_id)).size < 2 || new Set(playEntries.map(item => item.document.operator)).size < 2) throw evidenceError("gate play coverage is not independent by both context and operator", `/gates/${gate}/fixed_inputs/play_sessions`);
  if (typeof fixed.performance_plan !== "string" || !fixed.performance_plan) throw evidenceError("gate requires a frozen performance plan", `/gates/${gate}/fixed_inputs/performance_plan`);
  const performancePlanEntry = evidence.entries.find(item => item.id === fixed.performance_plan && (item.entry.kind === "performance-plan" || item.document.kind === "performance-plan"));
  if (!performancePlanEntry) throw evidenceError("gate references a missing performance plan", `/gates/${gate}/fixed_inputs/performance_plan`);
  const performancePlan = performancePlanEntry.facts?.scenarios ? performancePlanEntry.facts : validatePerformancePlan(performancePlanEntry.document);
  const performanceIds = fixed.performance_cells;
  if (!Array.isArray(performanceIds) || performanceIds.length === 0 || new Set(performanceIds).size !== performanceIds.length) throw evidenceError("gate performance coverage is incomplete", `/gates/${gate}/fixed_inputs/performance_cells`);
  const performanceEntries = performanceIds.map(id => evidence.entries.find(candidate => candidate.id === id && (candidate.entry.kind === "performance" || candidate.document.kind === "performance-cell")));
  if (performanceEntries.some(item => !item)) throw evidenceError("gate references a missing performance cell", `/gates/${gate}/fixed_inputs/performance_cells`);
  if (performanceEntries.some(item => item.document.source !== "live-browser" || item.document.status !== "complete" || item.document.qualification?.status !== "qualified")) throw evidenceError("fixture or unqualified performance evidence cannot pass a gate", `/gates/${gate}/fixed_inputs/performance_cells`);
  const performanceCoverage = validatePerformanceCoverage(performancePlan, performanceEntries, `/gates/${gate}/fixed_inputs/performance_cells`);
  const matrixEntry = evidence.entries.find(item => item.id === fixed.capture_matrix && item.document.kind === "capture-matrix");
  if (!matrixEntry) throw evidenceError("gate capture matrix identity is missing", `/gates/${gate}/fixed_inputs/capture_matrix`);
  if (matrixEntry.document.status !== "complete") throw evidenceError("gate capture matrix is not complete", `/gates/${gate}/fixed_inputs/capture_matrix`);
  for (const cell of matrixEntry.document.cells || []) {
    if (cell.required === false) continue;
    if (!Array.isArray(cell.capture_ids) || cell.capture_ids.length === 0 || cell.capture_ids.some(id => !evidence.ids.includes(id))) throw evidenceError(`required capture cell ${cell.id} is missing hashed evidence`, `/gates/${gate}/fixed_inputs/capture_matrix`);
    for (const captureId of cell.capture_ids) {
      const capture = evidence.entries.find(item => item.id === captureId && (item.entry.kind === "capture" || item.document.kind === "capture"));
      if (!capture) throw evidenceError(`capture ${captureId} is not a typed capture record`, `/gates/${gate}/fixed_inputs/capture_matrix`);
      const document = capture.document;
      if (canonicalJson(document.state) !== canonicalJson(cell.state) || canonicalJson(document.viewport) !== canonicalJson(cell.viewport) || Number(document.dpr) !== Number(cell.dpr)) throw evidenceError(`capture ${captureId} does not match matrix cell ${cell.id} state, viewport, and DPR`, `/gates/${gate}/fixed_inputs/capture_matrix/${cell.id}`);
    }
  }
  if (record.disposition !== "pass") throw evidenceError(`gate disposition is ${record.disposition}, not pass`, `/gates/${gate}/disposition`);
  if ((record.complaints || []).length || (record.gaps || []).length) throw evidenceError("gate has open complaints or gaps", `/gates/${gate}`);
  if (!index.promotion || index.promotion.validator !== "validate_evidence.mjs" || !index.promotion.result_identity) throw evidenceError("gate requires a validate_evidence.mjs promoted index", "/promotion");
  let lineage;
  try {
    lineage = await validateGateLineage(lineageInputs(index, gate, evidence.entries, record, baseDir));
  } catch (error) {
    if (error instanceof LineageError) throw evidenceError(`${error.lineageCode}: ${error.message}`, error.pointer);
    throw error;
  }
  return { status: "valid", gate, evidence_ids: evidence.ids, performance_coverage: performanceCoverage, lineage, disposition: "pass" };
}

async function main() {
  const argv = process.argv.slice(2);
  const command = argv[0] && !argv[0].startsWith("--") ? argv.shift() : null;
  const args = parseArgs(argv);
  // `gate` is a positional subcommand while `--gate core|final` carries its
  // value.  Do not overwrite that value with a boolean before dispatching.
  if (command && command !== "gate") args[command.replaceAll("-", "_")] = true;
  if (command === "gate" && typeof args.gate !== "string") throw inputError("gate command requires --gate core or --gate final", "/gate");
  let output;
  if (args.performance && args.cell) output = await validatePerformanceCell((await readJson(resolve(args.cell))).value);
  else if (args.asset && args.manifest) output = await validateAssetManifest((await readJson(resolve(args.manifest))).value, { baseDir: dirname(resolve(args.manifest)) });
  else if (args.gate && args.index) output = await validateGate((await readJson(resolve(args.index))).value, args.gate, { baseDir: dirname(resolve(args.index)) });
  else if (args.index) {
    const loaded = await readJson(resolve(args.index));
    const index = loaded.value;
    output = await validateEvidenceIndex(index, { baseDir: dirname(resolve(args.index)), allowDraft: Boolean(args.promote) });
    if (args.promote) {
      if (index.status !== "draft" || index.promotion) throw evidenceError("--promote accepts only an unpromoted draft evidence index", "/status");
      const resultIdentity = output.result_identity;
      index.promotion = { validator: "validate_evidence.mjs", observed_at: nowIso(), result_identity: resultIdentity };
      index.status = "complete";
      await writeJsonAtomic(resolve(args.index), index);
      output = { ...output, promoted: true, promotion: index.promotion };
    }
  }
  else throw inputError("choose performance --cell, asset --manifest, gate --index, or --index");
  process.stdout.write(`${JSON.stringify(output)}\n`);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replaceAll("\\", "/"))) {
  main().catch(error => { const result = resultFromError(error); process.stderr.write(`${result.result.error.message}\n`); process.stdout.write(`${JSON.stringify(result.result)}\n`); process.exitCode = result.exitCode; });
}

export { requireHeader, sessionClassification, canonicalTranscript, hashPath, validatePerformancePlan, validationReceipt };
