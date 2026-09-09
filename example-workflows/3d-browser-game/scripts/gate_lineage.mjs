/**
 * Typed provenance and repair-cycle checks for the browser-game gates.
 *
 * This module deliberately observes commit ancestry through a caller-owned
 * sourceObservation function (or an explicit fixture observation). A SHA-256
 * value identifies bytes; it cannot establish that one git revision descends
 * from another. The helper is pure with respect to run state and returns one
 * actionable diagnostic per violated invariant.
 */
import { canonicalJson, sha256 } from "./_common.mjs";

const COMMIT = /^(?:git:)?[0-9a-f]{40}$/i;
const HASH = /^sha256:[0-9a-f]{64}$/i;
const CLOSING_STATUSES = new Set(["fixed", "rejected", "superseded"]);
const OPEN_STATUSES = new Set(["open", "accepted"]);

export class LineageError extends Error {
  constructor(code, message, pointer = "/", expected = undefined, observed = undefined) {
    super(message);
    this.name = "LineageError";
    this.code = "evidence-failure";
    this.lineageCode = code;
    this.pointer = pointer;
    this.expected = expected;
    this.observed = observed;
  }
}

function fail(code, message, pointer, expected, observed) {
  throw new LineageError(code, message, pointer, expected, observed);
}

function commit(value, pointer) {
  if (typeof value !== "string" || !COMMIT.test(value)) fail("invalid-commit", "expected a full git commit identity", pointer, "git:<40 hex> or <40 hex>", value);
  return value.replace(/^git:/i, "").toLowerCase();
}

function identity(value, pointer) {
  if (typeof value !== "string" || value.length === 0) fail("invalid-identity", "expected a non-empty identity", pointer, "non-empty string", value);
  return value;
}

function hash(value, pointer) {
  if (typeof value !== "string" || !HASH.test(value)) fail("invalid-hash", "expected a sha256 identity", pointer, "sha256:<64 lowercase hex>", value);
  return value.toLowerCase();
}

function object(value, pointer) {
  if (!value || typeof value !== "object" || Array.isArray(value)) fail("invalid-record", "expected an object", pointer, "object", value);
  return value;
}

function array(value, pointer, required = true) {
  if (!Array.isArray(value) || (required && value.length === 0)) fail("invalid-array", required ? "expected a non-empty array" : "expected an array", pointer, required ? "non-empty array" : "array", value);
  return value;
}

function typed(value, expectedKind, pointer) {
  object(value, pointer);
  if (value.kind !== expectedKind) fail("wrong-kind", `expected typed ${expectedKind} record`, `${pointer}/kind`, expectedKind, value.kind);
  if (value.id !== undefined) identity(value.id, `${pointer}/id`);
  if (value.artifact_commit !== undefined) commit(value.artifact_commit, `${pointer}/artifact_commit`);
  return value;
}

function sameCommit(left, right) {
  return commit(left, "/commit") === commit(right, "/commit");
}

function first(...values) {
  return values.find(value => value !== undefined && value !== null);
}

function entriesOf(index) {
  return array(index.entries || index.evidence, "/evidence_index/entries", false);
}

function indexById(index) {
  const map = new Map();
  for (const [position, entry] of entriesOf(index).entries()) {
    object(entry, `/evidence_index/entries/${position}`);
    const document = entry.document || entry.value || entry.record;
    const id = entry.id || document?.id || entry.path;
    identity(id, `/evidence_index/entries/${position}/id`);
    if (map.has(id)) fail("duplicate-evidence-id", `evidence id ${id} is repeated`, `/evidence_index/entries/${position}/id`);
    map.set(id, entry);
  }
  return map;
}

function typedEntry(map, id, kinds, pointer) {
  identity(id, pointer);
  const entry = map.get(id);
  if (!entry) fail("missing-evidence", `missing evidence ${id}`, pointer, id, undefined);
  const expected = Array.isArray(kinds) ? kinds : [kinds];
  const entryKind = entry.kind;
  const document = entry.document || entry.value || entry.record;
  const documentKind = document?.kind;
  if (!expected.includes(entryKind) && !expected.includes(documentKind)) fail("wrong-evidence-kind", `evidence ${id} has kind ${entryKind || documentKind || "unknown"}`, pointer, expected, { entry: entryKind, document: documentKind });
  return { ...entry, document };
}

function currentCommit(input) {
  return commit(first(input.artifact?.current_commit, input.artifact?.artifact_commit, input.artifact_commit, input.evidenceIndex?.artifact_commit, input.gateVerdict?.artifact_commit), "/artifact_commit");
}

function promiseIds(brief, amendments = []) {
  const source = brief?.promises || brief?.promise_ids || brief?.requirements || brief?.rows;
  const found = [];
  if (Array.isArray(source)) for (const item of source) found.push(typeof item === "string" ? item : first(item?.id, item?.identity, item?.promise_id, item?.prompt_promise?.identity));
  if (Array.isArray(brief?.promise_ids)) found.push(...brief.promise_ids);
  for (const amendment of amendments) {
    const values = amendment?.promises || amendment?.promise_ids || amendment?.requirements || amendment?.rows;
    if (Array.isArray(values)) for (const item of values) found.push(typeof item === "string" ? item : first(item?.id, item?.identity, item?.promise_id, item?.prompt_promise?.identity));
  }
  const ids = found.filter(Boolean);
  if (ids.length === 0) return null;
  return new Set(ids.map((id, index) => identity(id, `/brief/promises/${index}`)));
}

function authorityIdentity(value, pointer) {
  if (!value) return null;
  object(value, pointer);
  const id = first(value.identity, value.id);
  const digest = first(value.sha256, value.hash);
  if (id !== undefined) identity(id, `${pointer}/identity`);
  if (digest !== undefined) hash(digest, `${pointer}/sha256`);
  return { id, digest };
}

function authoritySet(value, pointer) {
  if (!Array.isArray(value)) return new Map();
  const result = new Map();
  for (const [position, item] of value.entries()) {
    const authority = authorityIdentity(item, `${pointer}/${position}`);
    if (!authority?.id) fail("missing-authority-identity", "amendment needs a stable identity", `${pointer}/${position}`, "identity and sha256", item);
    if (!authority.digest) fail("missing-authority-hash", `authority ${authority.id} needs its original bytes hash`, `${pointer}/${position}/sha256`, "sha256 identity", item);
    result.set(authority.id, authority.digest);
  }
  return result;
}

function tracePromiseIds(traceability) {
  const rows = array(traceability.rows, "/traceability/rows");
  const ids = new Set();
  for (const [position, row] of rows.entries()) {
    object(row, `/traceability/rows/${position}`);
    const id = first(row.prompt_promise?.identity, row.prompt_promise?.id, row.promise_id);
    identity(id, `/traceability/rows/${position}/prompt_promise`);
    if (ids.has(id)) fail("duplicate-promise", `traceability repeats prompt promise ${id}`, `/traceability/rows/${position}/prompt_promise`);
    ids.add(id);
  }
  if (Array.isArray(traceability.promise_ids)) {
    const declared = new Set(traceability.promise_ids.map((id, position) => identity(id, `/traceability/promise_ids/${position}`)));
    if (declared.size !== ids.size || [...declared].some(id => !ids.has(id))) fail("traceability-row-set-mismatch", "declared promise_ids do not equal traceability rows", "/traceability/promise_ids", [...ids], [...declared]);
  }
  return ids;
}

function ancestryData(input) {
  const source = input.artifact || {};
  return {
    ancestors: source.ancestors || source.declared_ancestors || input.evidenceIndex?.declared_ancestors || [],
    map: source.ancestor_map || source.ancestorMap || {},
    observations: source.observations || source.ancestry || [],
  };
}

async function observedAncestor(ancestor, descendant, input, pointer) {
  const a = commit(ancestor, `${pointer}/ancestor`);
  const d = commit(descendant, `${pointer}/descendant`);
  if (a === d) return true;
  const observer = input.sourceObservation || input.observeSource || input.observeAncestry;
  if (typeof observer === "function") {
    const raw = observer.length <= 1
      ? await observer({ ancestor: `git:${a}`, descendant: `git:${d}`, pointer })
      : await observer(`git:${a}`, `git:${d}`);
    const result = typeof raw === "boolean" ? raw : first(raw?.isAncestor, raw?.ancestor, raw?.descends, raw?.status === "ancestor" || raw?.relation === "ancestor" ? true : undefined, raw?.status === "unrelated" || raw?.relation === "unrelated" ? false : undefined);
    if (result === true) return true;
    if (result === false) fail("unrelated-source-ancestry", "source observation says the claimed ancestor is unrelated", pointer, { ancestor: a, descendant: d }, raw);
    fail("unverified-source-ancestry", "source observation did not return an ancestry result", pointer, "boolean or {isAncestor:boolean}", raw);
  }
  const data = ancestryData(input);
  const listed = data.map[`git:${d}`] || data.map[d] || data.map[descendant];
  if (Array.isArray(listed) && listed.some(value => typeof value === "string" && value.replace(/^git:/i, "").toLowerCase() === a)) return true;
  if (Array.isArray(data.ancestors) && data.ancestors.some(value => typeof value === "string" && value.replace(/^git:/i, "").toLowerCase() === a)) return true;
  if (Array.isArray(data.observations)) {
    const row = data.observations.find(item => item && String(item.ancestor || "").replace(/^git:/i, "").toLowerCase() === a && String(item.descendant || item.artifact || "").replace(/^git:/i, "").toLowerCase() === d);
    if (row) {
      if (row.isAncestor === true || row.status === "ancestor" || row.relation === "ancestor") return true;
      fail("unrelated-source-ancestry", "source observation says the claimed ancestor is unrelated", pointer, { ancestor: a, descendant: d }, row);
    }
  }
  fail("unverified-source-ancestry", "commit ancestry needs a caller-owned source observation", pointer, { ancestor: a, descendant: d }, undefined);
}

function complaintMap(record, pointer) {
  const values = [...(record.complaints || []), ...(record.complaint_ledger || []), ...(record.lineage?.complaints || [])];
  const map = new Map();
  for (const [position, item] of values.entries()) {
    object(item, `${pointer}/complaints/${position}`);
    const id = identity(item.id, `${pointer}/complaints/${position}/id`);
    map.set(id, item);
  }
  return map;
}

function closure(item, pointer, entries) {
  const proof = first(item.closure, item.resolution, item.disposition);
  if (!proof || typeof proof !== "object") fail("missing-complaint-closure", `closed complaint ${item.id} needs explicit closure evidence`, pointer, "closure {reason,evidence}", proof);
  if (typeof proof.reason !== "string" || proof.reason.length === 0) fail("missing-complaint-closure", `closed complaint ${item.id} needs a closure reason`, `${pointer}/reason`, "non-empty reason", proof.reason);
  if (!Array.isArray(proof.evidence) || proof.evidence.length === 0) fail("missing-complaint-closure", `closed complaint ${item.id} needs closure evidence identities`, `${pointer}/evidence`, "non-empty identity array", proof.evidence);
  for (const [position, id] of proof.evidence.entries()) {
    identity(id, `${pointer}/evidence/${position}`);
    if (entries && !entries.has(id)) fail("missing-closure-evidence", `closure evidence ${id} is not indexed`, `${pointer}/evidence/${position}`, id, undefined);
  }
}

function predecessorOf(record) {
  const lineage = record.lineage || record.provenance || {};
  return {
    id: first(lineage.predecessor_id, lineage.predecessor, record.predecessor_id, record.predecessor),
    sha256: first(lineage.predecessor_sha256, lineage.predecessor_hash, record.predecessor_sha256, record.predecessor_hash),
    relation: first(lineage.relation, record.relation),
  };
}

function verifyPredecessorHash(successor, predecessor, pointer, suppliedHash, predecessorBytes) {
  const declared = predecessorOf(successor);
  if (declared.id && predecessor?.id && declared.id !== predecessor.id) fail("predecessor-id-mismatch", "successor names a different predecessor record", `${pointer}/predecessor`, predecessor.id, declared.id);
  const expected = first(suppliedHash, declared.sha256, predecessor?.record_hash, predecessor?.hash);
  if (!expected) fail("missing-predecessor-hash", "successor record must bind its predecessor bytes", `${pointer}/predecessor_sha256`, "sha256 identity", expected);
  hash(expected, `${pointer}/predecessor_sha256`);
  const observed = sha256(predecessorBytes === undefined ? canonicalJson(predecessor) : predecessorBytes);
  if (expected.toLowerCase() !== observed.toLowerCase()) fail("predecessor-hash-mismatch", "successor predecessor hash does not match predecessor bytes", `${pointer}/predecessor_sha256`, expected, observed);
}

function verifyComplaintLineage(successor, predecessor, pointer, entries) {
  if (!predecessor) return;
  typed(predecessor, "run-record", "/predecessor");
  const prior = complaintMap(predecessor, "/predecessor");
  if (prior.size === 0) return;
  const next = complaintMap(successor, "/run_record");
  for (const [id, old] of prior) {
    const current = next.get(id);
    if (!current) fail("deleted-complaint", `successor deleted prior complaint ${id}`, `${pointer}/complaints`, id, undefined);
    for (const field of ["seam", "kind", "cause"]) if (current[field] !== old[field]) fail("rewritten-complaint", `successor rewrote immutable complaint ${id} field ${field}`, `${pointer}/complaints/${id}/${field}`, old[field], current[field]);
    if (Array.isArray(old.evidence) && (!Array.isArray(current.evidence) || old.evidence.some(value => !current.evidence.includes(value)))) fail("rewritten-complaint", `successor rewrote evidence for complaint ${id}`, `${pointer}/complaints/${id}/evidence`, old.evidence, current.evidence);
    if (old.expected_improvement !== undefined && current.expected_improvement !== old.expected_improvement) fail("rewritten-complaint", `successor rewrote expected improvement for complaint ${id}`, `${pointer}/complaints/${id}/expected_improvement`, old.expected_improvement, current.expected_improvement);
    const previousStatus = old.status || "open";
    const currentStatus = current.status || "open";
    if (CLOSING_STATUSES.has(previousStatus) && OPEN_STATUSES.has(currentStatus)) fail("reopened-complaint", `successor reopened closed complaint ${id}`, `${pointer}/complaints/${id}/status`, previousStatus, currentStatus);
    if (currentStatus !== previousStatus) closure(current, `${pointer}/complaints/${id}/closure`, entries);
  }
}

function changedMechanics(input, runRecord, verdict, assets) {
  const values = [
    ...(input.changedMechanics || []), ...(runRecord?.lineage?.changed_mechanics || []), ...(runRecord?.changed_mechanics || []),
    ...(verdict?.changed_mechanics || []), ...(verdict?.fixed_inputs?.changed_mechanics || []),
  ];
  for (const asset of assets) {
    const doc = asset.document || asset;
    if (Array.isArray(doc.mechanics_changed)) values.push(...doc.mechanics_changed);
    if (Array.isArray(doc.changed_mechanics)) values.push(...doc.changed_mechanics);
    if (doc.gameplay_impact === "changed" || doc.gameplay_changing === true) values.push("gameplay");
  }
  return [...new Set(values.filter(value => typeof value === "string" && value.length > 0))];
}

function reproofObject(verdict, runRecord) {
  return first(verdict?.fixed_inputs?.affected_core_reproof, verdict?.fixed_inputs?.core_reproof, verdict?.affected_core_reproof, runRecord?.lineage?.affected_core_reproof, runRecord?.affected_core_reproof);
}

async function checkTraceability(input) {
  const trace = typed(input.traceability, "traceability", "/traceability");
  const brief = input.brief || input.originalBrief;
  const sourceIds = promiseIds(brief, input.amendments || input.runRecord?.amendments || []);
  if (!sourceIds) fail("missing-brief-promises", "cannot prove exhaustive traceability without an authoritative brief promise inventory", "/brief/promises", "non-empty promise inventory", undefined);
  const runBrief = authorityIdentity(input.runRecord.brief, "/run_record/brief");
  const suppliedBrief = authorityIdentity(brief, "/brief");
  const traceBrief = authorityIdentity(first(trace.brief, trace.source_brief, trace.authority, trace.brief_identity ? { identity: trace.brief_identity, sha256: trace.brief_sha256 } : undefined), "/traceability/brief");
  for (const [label, value] of [["run record", runBrief], ["traceability", traceBrief]]) {
    if (!value?.id || !value.digest) fail("unbound-original-brief", `${label} must bind the original brief identity and bytes hash`, label === "run record" ? "/run_record/brief" : "/traceability/brief", "identity and sha256", value);
    if (value.id !== suppliedBrief?.id || value.digest !== suppliedBrief?.digest) fail("brief-binding-mismatch", `${label} is bound to different original brief bytes`, label === "run record" ? "/run_record/brief" : "/traceability/brief", suppliedBrief, value);
  }
  const amendments = input.amendments || input.runRecord?.amendments || [];
  const runAmendments = authoritySet(input.runRecord.amendments, "/run_record/amendments");
  const traceAmendments = authoritySet(first(trace.amendments, trace.authority_amendments), "/traceability/amendments");
  const suppliedAmendments = authoritySet(amendments, "/amendments");
  if (runAmendments.size !== suppliedAmendments.size || [...suppliedAmendments].some(([id, digest]) => runAmendments.get(id) !== digest)) fail("amendment-binding-mismatch", "run record amendments do not preserve original amendment hashes", "/run_record/amendments", [...suppliedAmendments], [...runAmendments]);
  if (traceAmendments.size !== suppliedAmendments.size || [...suppliedAmendments].some(([id, digest]) => traceAmendments.get(id) !== digest)) fail("amendment-binding-mismatch", "traceability amendments do not preserve original amendment hashes", "/traceability/amendments", [...suppliedAmendments], [...traceAmendments]);
  const rows = tracePromiseIds(trace);
  if (rows.size !== sourceIds.size || [...sourceIds].some(id => !rows.has(id))) fail("omitted-prompt-promise", "traceability does not cover every original-brief promise", "/traceability/rows", [...sourceIds], [...rows]);
  for (const [position, row] of trace.rows.entries()) {
    if (!Array.isArray(row.playable_evidence_ids)) fail("missing-promise-evidence", "traceability row needs typed evidence IDs", `/traceability/rows/${position}/playable_evidence_ids`, "array", row.playable_evidence_ids);
    for (const [index, id] of row.playable_evidence_ids.entries()) typedEntry(input._entries, id, ["play-session", "capture", "increment", "asset", "manifest"], `/traceability/rows/${position}/playable_evidence_ids/${index}`);
  }
  return { promise_count: rows.size };
}

async function checkCore(input, entries, current) {
  const verdict = typed(input.gateVerdict, "gate-verdict", "/gate_verdict");
  if (verdict.gate !== "core") fail("wrong-gate", "lineage core check requires a core verdict", "/gate_verdict/gate", "core", verdict.gate);
  if (verdict.disposition !== "pass") fail("core-not-accepted", "core gate must be accepted before production art", "/gate_verdict/disposition", "pass", verdict.disposition);
  if (verdict.status && !["ready", "complete"].includes(verdict.status)) fail("core-not-accepted", "core verdict is not a complete accepted record", "/gate_verdict/status", ["ready", "complete"], verdict.status);
  if (Array.isArray(verdict.gaps) && verdict.gaps.length) fail("core-has-gaps", "accepted core verdict still declares gaps", "/gate_verdict/gaps", [], verdict.gaps);
  if (Array.isArray(verdict.complaints) && verdict.complaints.length) fail("core-has-complaints", "accepted core verdict still declares complaints", "/gate_verdict/complaints", [], verdict.complaints);
  const fixed = object(verdict.fixed_inputs, "/gate_verdict/fixed_inputs");
  const fixedCommit = commit(first(fixed.artifact_commit, verdict.artifact_commit), "/gate_verdict/fixed_inputs/artifact_commit");
  if (fixedCommit !== current) fail("core-baseline-mismatch", "core fixed baseline does not match the core artifact", "/gate_verdict/fixed_inputs/artifact_commit", current, fixedCommit);
  return { gate: "core", artifact_commit: `git:${fixedCommit}`, verdict_id: verdict.id };
}

async function checkFinal(input, entries, current) {
  const verdict = typed(input.gateVerdict, "gate-verdict", "/gate_verdict");
  if (verdict.gate !== "final") fail("wrong-gate", "lineage final check requires a final verdict", "/gate_verdict/gate", "final", verdict.gate);
  if (verdict.disposition !== "pass") fail("final-not-accepted", "final gate must be accepted", "/gate_verdict/disposition", "pass", verdict.disposition);
  const fixed = object(verdict.fixed_inputs, "/gate_verdict/fixed_inputs");
  const coreId = first(fixed.accepted_core_verdict, fixed.core_gate_verdict, fixed.core_verdict, input.coreGateVerdict?.id);
  if (!coreId) fail("missing-core-baseline", "final gate must name an accepted core verdict", "/gate_verdict/fixed_inputs/core_gate_verdict", "typed core verdict identity", coreId);
  const coreEntry = entries.get(coreId);
  const core = input.coreGateVerdict || coreEntry?.document || coreEntry?.value;
  typed(core, "gate-verdict", "/core_gate_verdict");
  if (core.gate !== "core" || core.disposition !== "pass") fail("core-not-accepted", "final gate core baseline is not an accepted core verdict", "/core_gate_verdict", "gate=core, disposition=pass", { gate: core.gate, disposition: core.disposition });
  const coreCommit = commit(first(core.artifact_commit, core.fixed_inputs?.artifact_commit), "/core_gate_verdict/artifact_commit");
  await observedAncestor(`git:${coreCommit}`, `git:${current}`, input, "/lineage/core_to_final");
  const conceptIds = first(fixed.concept_artifacts, fixed.concept_artifact_ids, input.conceptArtifacts);
  const assetIds = first(fixed.asset_manifests, fixed.asset_manifest_ids, input.assetManifests);
  if (!Array.isArray(conceptIds) || conceptIds.length === 0) fail("missing-concept-provenance", "final gate must name post-core concept provenance", "/gate_verdict/fixed_inputs/concept_artifacts", "non-empty identity array", conceptIds);
  if (!Array.isArray(assetIds) || assetIds.length === 0) fail("missing-asset-provenance", "final gate must name production asset manifests", "/gate_verdict/fixed_inputs/asset_manifests", "non-empty identity array", assetIds);
  const descended = [];
  for (const id of conceptIds) {
    const entry = typedEntry(entries, id, ["concept"], "/gate_verdict/fixed_inputs/concept_artifacts");
    const doc = entry.document || {};
    if (doc.kind && !["concept", "concept-art"].includes(doc.kind)) fail("wrong-evidence-kind", `concept evidence ${id} is not typed concept art`, `/evidence/${id}/kind`, "concept", doc.kind);
    const artifact = commit(first(doc.artifact_commit, entry.source_commit), `/evidence/${id}/artifact_commit`);
    await observedAncestor(`git:${coreCommit}`, `git:${artifact}`, input, `/lineage/concept/${id}`);
    descended.push(entry);
  }
  for (const id of assetIds) {
    const entry = typedEntry(entries, id, ["asset", "manifest"], "/gate_verdict/fixed_inputs/asset_manifests");
    const doc = entry.document || {};
    if (doc.kind && doc.kind !== "asset-manifest") fail("wrong-evidence-kind", `asset evidence ${id} is not a typed asset-manifest`, `/evidence/${id}/kind`, "asset-manifest", doc.kind);
    if (entry.kind !== "asset" && entry.kind !== "manifest") fail("wrong-evidence-kind", `asset evidence ${id} is not indexed as an asset or manifest`, `/evidence/${id}/kind`, ["asset", "manifest"], entry.kind);
    const artifact = commit(first(doc.artifact_commit, entry.source_commit), `/evidence/${id}/artifact_commit`);
    await observedAncestor(`git:${coreCommit}`, `git:${artifact}`, input, `/lineage/asset/${id}`);
    descended.push(entry);
  }
  const changed = changedMechanics(input, input.runRecord, verdict, descended);
  if (changed.length) {
    const reproof = reproofObject(verdict, input.runRecord);
    if (!reproof) fail("missing-core-reproof", "gameplay-changing integration requires affected-core reproof", "/gate_verdict/fixed_inputs/affected_core_reproof", "typed reproof", reproof);
    const reproofVerdict = input.coreReproof || reproof.verdict_record || reproof.record;
    if (!reproofVerdict) fail("missing-core-reproof", "affected-core reproof must carry its typed verdict record", "/gate_verdict/fixed_inputs/affected_core_reproof/verdict", "gate-verdict", undefined);
    typed(reproofVerdict, "gate-verdict", "/affected_core_reproof/verdict");
    if (reproofVerdict.gate !== "core" || reproofVerdict.disposition !== "pass") fail("invalid-core-reproof", "affected-core reproof must be an accepted core verdict", "/affected_core_reproof/verdict", "gate=core, disposition=pass", reproofVerdict);
    const reproofCommit = commit(first(reproof.artifact_commit, reproofVerdict.artifact_commit, reproofVerdict.fixed_inputs?.artifact_commit), "/affected_core_reproof/artifact_commit");
    await observedAncestor(`git:${reproofCommit}`, `git:${current}`, input, "/lineage/reproof_to_final");
    if (!Array.isArray(reproof.changed_mechanics) || reproof.changed_mechanics.length === 0) fail("incomplete-core-reproof", "affected-core reproof must enumerate changed mechanics", "/affected_core_reproof/changed_mechanics", changed, reproof.changed_mechanics);
    if (changed.some(value => !reproof.changed_mechanics.includes(value))) fail("incomplete-core-reproof", "affected-core reproof does not cover every changed mechanic", "/affected_core_reproof/changed_mechanics", changed, reproof.changed_mechanics);
    for (const source of descended.filter(entry => {
      const doc = entry.document || {};
      return Array.isArray(doc.mechanics_changed) || Array.isArray(doc.changed_mechanics) || doc.gameplay_impact === "changed" || doc.gameplay_changing === true;
    })) {
      const sourceCommit = commit(first(source.document?.artifact_commit, source.entry?.source_commit, source.source_commit), `/evidence/${source.id}/artifact_commit`);
      await observedAncestor(`git:${sourceCommit}`, `git:${reproofCommit}`, input, `/lineage/reproof_after/${source.id}`);
    }
  }
  return { gate: "final", artifact_commit: `git:${current}`, core_verdict_id: core.id, concept_count: conceptIds.length, asset_manifest_count: assetIds.length, reproof: changed.length > 0 };
}

/**
 * Validate one gate's provenance. The returned object is intentionally small
 * so validate_evidence can include it in its own portable receipt.
 */
export async function validateGateLineage(input = {}) {
  object(input, "/");
  typed(input.runRecord, "run-record", "/run_record");
  typed(input.traceability, "traceability", "/traceability");
  typed(input.evidenceIndex, "evidence-index", "/evidence_index");
  typed(input.gateVerdict, "gate-verdict", "/gate_verdict");
  const gate = first(input.gate, input.gateVerdict.gate);
  const current = currentCommit(input);
  const entries = indexById(input.evidenceIndex);
  input._entries = entries;
  if (input.evidenceIndex.artifact_commit && !sameCommit(input.evidenceIndex.artifact_commit, current) && !(input.gate === "core" && input.historical_core === true)) fail("artifact-mismatch", "evidence index and selected artifact differ", "/evidence_index/artifact_commit", current, input.evidenceIndex.artifact_commit);
  if (input.gateVerdict.artifact_commit && input.gate === "final" && !sameCommit(input.gateVerdict.artifact_commit, current)) fail("artifact-mismatch", "final verdict is not bound to the selected artifact", "/gate_verdict/artifact_commit", current, input.gateVerdict.artifact_commit);
  const predecessor = input.predecessorRunRecord || input.predecessor?.runRecord || input.predecessor;
  if (predecessor) {
    verifyPredecessorHash(input.runRecord, predecessor, "/run_record/lineage", first(input.predecessorHash, input.predecessor_sha256), input.predecessorBytes);
    verifyComplaintLineage(input.runRecord, predecessor, "/run_record/lineage", entries);
  } else if (gate === "final") {
    const declared = predecessorOf(input.runRecord);
    if (declared.id || declared.sha256) fail("missing-predecessor-record", "successor names a predecessor but no typed predecessor record was supplied", "/run_record/lineage/predecessor", "typed run-record", undefined);
    fail("missing-predecessor-record", "final acceptance must carry the predecessor run record", "/run_record/lineage/predecessor", "typed run-record", undefined);
  }
  const trace = await checkTraceability(input);
  const result = gate === "core" ? await checkCore(input, entries, current) : gate === "final" ? await checkFinal(input, entries, current) : fail("invalid-gate", "gate must be core or final", "/gate", ["core", "final"], gate);
  return { status: "valid", diagnostics: [], ...result, traceability: trace, predecessor: predecessor ? { id: predecessor.id, hash: sha256(canonicalJson(predecessor)) } : null };
}

export const validateLineage = validateGateLineage;
export const checkGateLineage = validateGateLineage;

export function lineageDiagnostic(error) {
  if (!(error instanceof LineageError)) return { code: "unexpected-lineage-error", pointer: "/", message: error?.message || String(error) };
  return { code: error.lineageCode, pointer: error.pointer, message: error.message, expected: error.expected, observed: error.observed };
}
