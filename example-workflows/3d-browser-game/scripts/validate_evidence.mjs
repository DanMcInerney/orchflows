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
  for (const item of transcript) {
    if (!item || typeof item !== "object" || !item.command) throw evidenceError("transcript item lacks command", "/transcript");
    const command = item.command;
    try { validateCommand(command); } catch (error) { throw evidenceError(`invalid ordinary-input command: ${error.message}`, "/transcript/command"); }
    if (!allowed.has(command.type)) throw evidenceError(`unsupported transcript command ${command.type}`, "/transcript/command/type");
    if (command.type === "observe" || command.type === "capture") observed = true;
    if (observed && ["key", "pointer"].includes(command.type)) adapted = true;
    const sequence = item.reply?.sequence;
    if (sequence !== undefined) {
      if (!Number.isInteger(sequence) || sequence <= previousSequence) throw evidenceError("transcript reply sequence is not strictly increasing", "/transcript/reply/sequence");
      previousSequence = sequence;
    }
  }
  const requested = session.classification || session.input_mode;
  if (!["actual_play", "scripted_input", "simulated"].includes(requested)) throw evidenceError(`invalid play classification ${requested}`, "/classification");
  if (requested === "actual_play") {
    if (!session.operator || !session.independent_context_id) throw evidenceError("actual play requires operator and independent_context_id", "/classification");
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
  const qualification = qualifyPerformance({ cell: document.cell, trace: document.trace, callbacks: document.callbacks });
  if (qualification.status !== "qualified") throw evidenceError("performance: unverified", "/qualification");
  return { status: "valid", qualification };
}

export async function validateAssetManifest(manifest, { baseDir = process.cwd() } = {}) {
  requireHeader(manifest, "asset-manifest");
  const glb = manifest.glb || manifest.runtime || manifest.outputs?.glb || {};
  const glbPath = glb.path || manifest.glb_path || manifest.outputs?.glb_path;
  const expectedHash = glb.hash || glb.sha256 || manifest.glb_hash || manifest.hashes?.glb;
  if (!glbPath || !expectedHash) throw evidenceError("asset manifest needs a relative GLB path and hash", "/glb");
  resultIdentity(expectedHash);
  const observed = await hashPath(baseDir, glbPath, "/glb/path");
  if (observed.hash !== expectedHash) throw evidenceError(`GLB hash mismatch: expected ${expectedHash}, observed ${observed.hash}`, "/glb/hash");
  const khronos = manifest.validation?.khronos || manifest.validators?.khronos || manifest.khronos;
  const loader = manifest.validation?.gltf_loader || manifest.validation?.GLTFLoader || manifest.gltf_loader;
  if (!khronos || Number(khronos.errors) !== 0) throw evidenceError("pinned Khronos validation did not report zero errors", "/validation/khronos/errors");
  if (!loader || loader.status !== "pass" || !loader.evidence_id || !loader.artifact_commit) throw evidenceError("target GLTFLoader proof is missing or not passed", "/validation/gltf_loader");
  if (loader.glb_hash && loader.glb_hash !== expectedHash) throw evidenceError("GLTFLoader proof is bound to a different GLB", "/validation/gltf_loader/glb_hash");
  return { status: "valid", glb: { path: observed.path, hash: observed.hash }, khronos_errors: Number(khronos.errors), gltf_loader: loader.evidence_id };
}

async function validateCapture(document, { baseDir = process.cwd() } = {}) {
  requireHeader(document, "capture");
  const capture = document.capture || document.screenshot || {};
  if (!capture.path && !capture.hash && !capture.sha256) throw evidenceError("capture evidence needs a hashed screenshot artifact", "/capture");
  if (capture.path) {
    const observed = await hashPath(baseDir, capture.path, "/capture/path");
    const expected = capture.hash || capture.sha256;
    if (expected && observed.hash !== expected) throw evidenceError("capture screenshot hash mismatch", "/capture/hash");
  }
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
  if (!index.promotion && !(allowDraft && index.status === "draft")) throw evidenceError("evidence index is not promoted by validate_evidence.mjs", "/promotion");
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
  if (!Array.isArray(record.hard_gates) || !record.hard_gates.length) throw evidenceError("gate hard_gates are incomplete", `/gates/${gate}/hard_gates`);
  for (const hard of record.hard_gates) {
    const hardEvidence = hard?.evidence || hard?.evidence_ids;
    if (!hard || typeof hard !== "object" || !hard.id || !Array.isArray(hardEvidence) || hardEvidence.length === 0) throw evidenceError("each hard gate needs evidence identities; booleans cannot self-qualify", `/gates/${gate}/hard_gates`);
    if (hard.result !== "pass" && hard.result !== true && hard.status !== "pass") throw evidenceError(`hard gate ${hard.id} is not passed`, `/gates/${gate}/hard_gates/${hard.id}`);
    for (const id of hardEvidence) if (!evidence.ids.includes(id)) throw evidenceError(`hard gate ${hard.id} references missing evidence ${id}`, `/gates/${gate}/hard_gates/${hard.id}`);
  }
  const dimensions = record.dimensions || record.scores;
  if (!Array.isArray(dimensions) || dimensions.length === 0) throw evidenceError("gate dimensions are incomplete", `/gates/${gate}/scores`);
  for (const dimension of dimensions) {
    if (!Number.isInteger(dimension.score) || dimension.score < 0 || dimension.score > 4 || dimension.score < (dimension.floor ?? 3)) throw evidenceError(`dimension ${dimension.id || dimension.dimension || "unknown"} is below its floor`, `/gates/${gate}/scores`);
  }
  const fixed = record.fixed_inputs || {};
  const playIds = record.play_session_ids || record.play_ids || fixed.play_sessions || [];
  if (!Array.isArray(playIds) || new Set(playIds).size < 2) throw evidenceError("gate requires two independent play contexts", `/gates/${gate}/play_session_ids`);
  const playEntries = evidence.entries.filter(item => playIds.includes(item.id));
  if (playEntries.length !== playIds.length || new Set(playEntries.map(item => item.document.independent_context_id)).size < 2 || playEntries.some(item => item.document.kind !== "play-session" || item.document.classification !== "actual_play")) throw evidenceError("gate play coverage is not two independent actual-play contexts", `/gates/${gate}/play_session_ids`);
  const performanceIds = record.performance_cell_ids || fixed.performance_cells || [];
  if (!Array.isArray(performanceIds) || performanceIds.length === 0) throw evidenceError("gate performance coverage is incomplete", `/gates/${gate}/performance_cell_ids`);
  const performanceEntries = [];
  for (const id of performanceIds) {
    const item = evidence.entries.find(candidate => candidate.id === id && (candidate.entry.kind === "performance" || candidate.document.kind === "performance-cell"));
    if (!item) throw evidenceError(`missing performance cell ${id}`, `/gates/${gate}/performance_cell_ids`);
    performanceEntries.push(item);
  }
  const animated = performanceEntries.filter(item => item.document.cell?.mode !== "static" && item.document.cell?.mode !== "static-idle");
  if (animated.length && (animated.length < 3 || animated.some(item => Number(item.document.cell?.duration_seconds || ((item.document.cell?.window?.end_ms - item.document.cell?.window?.start_ms) / 1000)) < 60))) throw evidenceError("animation performance coverage requires three warm 60-second runs", `/gates/${gate}/performance_cell_ids`);
  if (fixed.capture_matrix && !evidence.entries.some(item => item.id === fixed.capture_matrix && item.document.kind === "capture-matrix")) throw evidenceError("gate capture matrix identity is missing", `/gates/${gate}/fixed_inputs/capture_matrix`);
  if (record.disposition !== "pass") throw evidenceError(`gate disposition is ${record.disposition}, not pass`, `/gates/${gate}/disposition`);
  if ((record.open_complaints || record.complaints || []).length || (record.gaps || []).length) throw evidenceError("gate has open complaints or gaps", `/gates/${gate}`);
  if (!index.promotion || index.promotion.validator !== "validate_evidence.mjs" || !index.promotion.result_identity) throw evidenceError("gate requires a validate_evidence.mjs promoted index", "/promotion");
  return { status: "valid", gate, evidence_ids: evidence.ids, disposition: "pass" };
}

async function main() {
  const argv = process.argv.slice(2);
  const command = argv[0] && !argv[0].startsWith("--") ? argv.shift() : null;
  const args = parseArgs(argv);
  if (command) args[command.replaceAll("-", "_")] = true;
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
