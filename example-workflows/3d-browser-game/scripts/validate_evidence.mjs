/**
 * Evidence admission is identity based. It re-hashes referenced bytes and
 * recomputes performance/session facts; a stored `passed: true` never becomes
 * acceptance evidence by itself.
 */
import { readFile } from "node:fs/promises";
import { resolve, relative, isAbsolute, dirname } from "node:path";
import { parseArgs, readJson, resultFromError, sha256, inputError, evidenceError, ensureContained, requireObject, nowIso, writeJsonAtomic, canonicalJson } from "./_common.mjs";
import { qualifyPerformance } from "./trace_frames.mjs";
import { validateCommand } from "./browser_harness.mjs";

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

function sessionClassification(session) {
  const transcript = session.transcript;
  if (!Array.isArray(transcript)) throw evidenceError("play session transcript must be an array", "/transcript");
  const allowed = new Set(["observe", "key", "pointer", "wait", "capture", "stop"]);
  let observed = false;
  let adapted = false;
  let previousSequence = 0;
  let stopped = false;
  for (const item of transcript) {
    if (!item || typeof item !== "object" || !item.command) throw evidenceError("transcript item lacks command", "/transcript");
    const command = item.command;
    try { validateCommand(command); } catch (error) { throw evidenceError(`invalid ordinary-input command: ${error.message}`, "/transcript/command"); }
    if (!allowed.has(command.type)) throw evidenceError(`unsupported transcript command ${command.type}`, "/transcript/command/type");
    if (!item.reply || typeof item.reply !== "object" || !Number.isInteger(item.reply.sequence) || typeof item.reply.status !== "string") throw evidenceError("every transcript command needs an observed sequence and status reply", "/transcript/reply");
    if (command.type === "observe" || command.type === "capture") observed = true;
    if (observed && ["key", "pointer"].includes(command.type)) adapted = true;
    const sequence = item.reply?.sequence;
    if (sequence !== undefined) {
      if (!Number.isInteger(sequence) || sequence <= previousSequence) throw evidenceError("transcript reply sequence is not strictly increasing", "/transcript/reply/sequence");
      previousSequence = sequence;
    }
    if (command.type === "stop") stopped = true;
  }
  if (!transcript.length || !stopped || transcript.at(-1).command.type !== "stop") throw evidenceError("play session must end with an observed stop command", "/transcript");
  const requested = session.classification || session.input_mode;
  if (!["actual_play", "scripted_input", "simulated"].includes(requested)) throw evidenceError(`invalid play classification ${requested}`, "/classification");
  if (requested === "actual_play") {
    if (!session.operator || !session.independent_context_id) throw evidenceError("actual play requires operator and independent_context_id", "/classification");
    if (session.source !== "live-browser") throw evidenceError("actual play requires a live-browser session source", "/source");
    if (session.headed !== true && session.environment?.headed !== true && session.browser?.headed !== true) throw evidenceError("actual play requires headed evidence", "/headed");
    if (!adapted) throw evidenceError("actual play requires an observation before later ordinary input", "/transcript");
  }
  if (session.transcript_hash && session.transcript_hash !== sha256(JSON.stringify(transcript, (_key, item) => item === undefined ? undefined : item))) {
    // Harness uses canonical JSON. This branch is a diagnostic for old or
    // hand-written sessions; canonical comparison below is authoritative.
  }
  return { requested, observations: transcript.filter(item => item.command.type === "observe").length, adapted };
}

export function validatePlaySession(session) {
  requireHeader(session, "play-session");
  const facts = sessionClassification(session);
  if (session.transcript_hash && session.transcript_hash !== sha256(canonicalTranscript(session.transcript))) throw evidenceError("transcript_hash does not match immutable transcript bytes", "/transcript_hash");
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
  if (!document.cell || !document.trace || !Array.isArray(document.callbacks)) throw evidenceError("performance result must preserve cell, trace, and callback samples", "/");
  if (!["live-browser", "qualification-fixture"].includes(document.source)) throw evidenceError("performance result must declare live-browser or qualification-fixture source", "/source");
  if (document.cell.artifact_commit !== document.artifact_commit) throw evidenceError("performance cell and result are bound to different artifact commits", "/cell/artifact_commit");
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
  await runPinnedKhronosValidator(observed.bytes, "/validation/khronos");
  if (!loader || loader.status !== "pass" || !loader.evidence_id || !loader.artifact_commit || loader.artifact_commit !== manifest.artifact_commit || loader.glb_hash !== expectedHash) throw evidenceError("target GLTFLoader proof is missing, not passed, or bound to another GLB/artifact", "/validation/gltf_loader");
  const loaderEvidence = await readEvidenceJson(baseDir, loader.evidence_path, loader.evidence_sha256, "/validation/gltf_loader", "GLTFLoader evidence");
  if (loaderEvidence.value.id !== loader.evidence_id || loaderEvidence.value.artifact_commit !== manifest.artifact_commit || loaderEvidence.value.glb_hash !== expectedHash) throw evidenceError("GLTFLoader evidence identity is not bound to this artifact and GLB", "/validation/gltf_loader/evidence_path");
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
  const observed = await hashPath(baseDir, capture.path, "/capture/path");
  if (observed.hash !== capture.hash) throw evidenceError("capture screenshot hash mismatch", "/capture/hash");
  if (!document.viewport || !Number.isFinite(document.dpr) || !document.state) throw evidenceError("capture lacks viewport, DPR, or state binding", "/capture");
  return { status: "valid" };
}

function validateCaptureMatrix(document) {
  requireHeader(document, "capture-matrix");
  if (!Array.isArray(document.cells) || document.cells.length === 0) throw evidenceError("capture matrix has no cells", "/cells");
  const ids = new Set();
  for (const cell of document.cells) {
    if (!cell || typeof cell.id !== "string" || ids.has(cell.id)) throw evidenceError("capture matrix cells need unique ids", "/cells");
    ids.add(cell.id);
    if (cell.required !== false && (!Array.isArray(cell.capture_ids) || cell.capture_ids.length === 0) && document.status === "complete") throw evidenceError(`required capture cell ${cell.id} is missing capture evidence`, `/cells/${cell.id}`);
  }
  return { status: "valid", cells: document.cells.length };
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
  if (document.kind === "play-session" || entry.kind === "play-session") validatePlaySession(document);
  if (document.kind === "performance-cell" || entry.kind === "performance") await validatePerformanceCell(document);
  if (document.kind === "asset-manifest" || entry.kind === "manifest" || entry.kind === "asset") await validateAssetManifest(document, { baseDir: dirname(observed.target) });
  if (document.kind === "capture" || entry.kind === "capture") await validateCapture(document, { baseDir: dirname(observed.target) });
  if (document.kind === "capture-matrix") validateCaptureMatrix(document);
  return { entry, document, observed, id: identity };
}

export async function validateEvidenceIndex(index, { baseDir = process.cwd(), allowDraft = false } = {}) {
  requireHeader(index, "evidence-index");
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
  return { status: "valid", ids: [...ids], entries: loaded, kinds: Object.fromEntries(kinds) };
}

export async function validateGate(index, gate, { baseDir = process.cwd() } = {}) {
  const evidence = await validateEvidenceIndex(index, { baseDir });
  const record = index.gates?.[gate] || evidence.entries.map(item => item.document).find(document => document.kind === "gate-verdict" && document.gate === gate);
  if (!record) throw evidenceError(`missing ${gate} gate record`, `/gates/${gate}`);
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
    for (const id of hard.evidence) if (!evidence.ids.includes(id)) throw evidenceError(`hard gate ${hard.id} references missing evidence ${id}`, `/gates/${gate}/hard_gates/${hard.id}`);
  }
  const dimensions = record.scores;
  const requiredDimensions = gate === "core" ? CORE_DIMENSION_IDS : FINAL_DIMENSION_IDS;
  if (!Array.isArray(dimensions) || dimensions.length !== requiredDimensions.length) throw evidenceError(`gate must score exactly ${requiredDimensions.length} frozen dimensions`, `/gates/${gate}/scores`);
  const dimensionIds = dimensions.map(item => item?.dimension);
  if (new Set(dimensionIds).size !== dimensionIds.length || requiredDimensions.some(id => !dimensionIds.includes(id)) || dimensionIds.some(id => !requiredDimensions.includes(id))) throw evidenceError("gate dimension identities do not match the frozen rubric", `/gates/${gate}/scores`);
  for (const dimension of dimensions) {
    if (!Number.isInteger(dimension.score) || dimension.score < 0 || dimension.score > 4 || dimension.score < CRITICAL_SCORE_FLOOR || (dimension.floor !== undefined && dimension.floor !== CRITICAL_SCORE_FLOOR)) throw evidenceError(`dimension ${dimension.dimension || "unknown"} is below the frozen floor of ${CRITICAL_SCORE_FLOOR}`, `/gates/${gate}/scores`);
    if (!Array.isArray(dimension.evidence) || dimension.evidence.length === 0 || dimension.evidence.some(id => !evidence.ids.includes(id))) throw evidenceError(`dimension ${dimension.dimension} lacks bound evidence`, `/gates/${gate}/scores`);
  }
  const fixed = record.fixed_inputs || {};
  if (fixed.artifact_commit !== index.artifact_commit) throw evidenceError("gate fixed inputs are bound to a different artifact commit", `/gates/${gate}/fixed_inputs/artifact_commit`);
  if (fixed.evidence_index !== index.id) throw evidenceError("gate fixed inputs must name this promoted evidence index", `/gates/${gate}/fixed_inputs/evidence_index`);
  for (const key of ["traceability", "rubric_revision"]) {
    if (typeof fixed[key] !== "string" || !evidence.ids.includes(fixed[key])) throw evidenceError(`gate fixed input ${key} is not bound to evidence`, `/gates/${gate}/fixed_inputs/${key}`);
  }
  if (!Array.isArray(fixed.play_sessions) || fixed.play_sessions.length < 2 || new Set(fixed.play_sessions).size !== fixed.play_sessions.length) throw evidenceError("gate requires two independent play contexts", `/gates/${gate}/fixed_inputs/play_sessions`);
  const playEntries = fixed.play_sessions.map(id => evidence.entries.find(item => item.id === id));
  if (playEntries.some(item => !item)) throw evidenceError("gate references a missing play session", `/gates/${gate}/fixed_inputs/play_sessions`);
  if (playEntries.some(item => item.document.kind !== "play-session" || item.document.classification !== "actual_play" || item.document.source !== "live-browser" || item.document.headed !== true || typeof item.document.operator !== "string" || !item.document.operator || typeof item.document.independent_context_id !== "string" || !item.document.independent_context_id)) throw evidenceError("gate play coverage requires live headed actual-play provenance", `/gates/${gate}/fixed_inputs/play_sessions`);
  if (new Set(playEntries.map(item => item.document.independent_context_id)).size < 2 || new Set(playEntries.map(item => item.document.operator)).size < 2) throw evidenceError("gate play coverage is not independent by both context and operator", `/gates/${gate}/fixed_inputs/play_sessions`);
  const performanceIds = fixed.performance_cells;
  if (!Array.isArray(performanceIds) || performanceIds.length === 0 || new Set(performanceIds).size !== performanceIds.length) throw evidenceError("gate performance coverage is incomplete", `/gates/${gate}/fixed_inputs/performance_cells`);
  const performanceEntries = performanceIds.map(id => evidence.entries.find(candidate => candidate.id === id && (candidate.entry.kind === "performance" || candidate.document.kind === "performance-cell")));
  if (performanceEntries.some(item => !item)) throw evidenceError("gate references a missing performance cell", `/gates/${gate}/fixed_inputs/performance_cells`);
  if (performanceEntries.some(item => item.document.source !== "live-browser" || item.document.status !== "complete" || item.document.qualification?.status !== "qualified")) throw evidenceError("fixture or unqualified performance evidence cannot pass a gate", `/gates/${gate}/fixed_inputs/performance_cells`);
  const animated = performanceEntries.filter(item => !["static", "static-idle"].includes(item.document.cell?.mode || item.document.cell?.surface));
  if (animated.length && (animated.length < 3 || animated.some(item => Number(item.document.cell?.duration_seconds || ((item.document.cell?.window?.end_ms - item.document.cell?.window?.start_ms) / 1000)) < 60))) throw evidenceError("animation performance coverage requires three warm 60-second runs", `/gates/${gate}/fixed_inputs/performance_cells`);
  if (animated.length >= 3) {
    const signature = item => canonicalJson(Object.fromEntries(Object.entries(item.document.cell || {}).filter(([key]) => !["id", "run_id", "run", "attempt", "warmup_index"].includes(key))));
    if (new Set(animated.map(signature)).size !== 1) throw evidenceError("animation performance runs must use one identical frozen cell", `/gates/${gate}/fixed_inputs/performance_cells`);
  }
  const matrixEntry = evidence.entries.find(item => item.id === fixed.capture_matrix && item.document.kind === "capture-matrix");
  if (!matrixEntry) throw evidenceError("gate capture matrix identity is missing", `/gates/${gate}/fixed_inputs/capture_matrix`);
  if (matrixEntry.document.status !== "complete") throw evidenceError("gate capture matrix is not complete", `/gates/${gate}/fixed_inputs/capture_matrix`);
  for (const cell of matrixEntry.document.cells || []) if (cell.required !== false && (!Array.isArray(cell.capture_ids) || cell.capture_ids.length === 0 || cell.capture_ids.some(id => !evidence.ids.includes(id)))) throw evidenceError(`required capture cell ${cell.id} is missing hashed evidence`, `/gates/${gate}/fixed_inputs/capture_matrix`);
  if (record.disposition !== "pass") throw evidenceError(`gate disposition is ${record.disposition}, not pass`, `/gates/${gate}/disposition`);
  if ((record.complaints || []).length || (record.gaps || []).length) throw evidenceError("gate has open complaints or gaps", `/gates/${gate}`);
  if (!index.promotion || index.promotion.validator !== "validate_evidence.mjs" || !index.promotion.result_identity) throw evidenceError("gate requires a validate_evidence.mjs promoted index", "/promotion");
  return { status: "valid", gate, evidence_ids: evidence.ids, disposition: "pass" };
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
      const resultIdentity = sha256(canonicalJson(output));
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

export { requireHeader, sessionClassification, canonicalTranscript, hashPath };
