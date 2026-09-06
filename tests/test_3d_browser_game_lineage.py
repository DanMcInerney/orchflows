"""Executable acceptance fixtures for the 3D browser-game lineage seam."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


# This test resolves its repository-owned fixture and package paths from the
# checkout root; the climb belongs to this test owner, not a wildcard exemption.
ROOT = Path(__file__).resolve().parents[1]
MODULE = "./example-workflows/3d-browser-game/scripts/gate_lineage.mjs"


SCRIPT = r'''
import {validateGateLineage, lineageDiagnostic} from "./example-workflows/3d-browser-game/scripts/gate_lineage.mjs";
import {canonicalJson, sha256} from "./example-workflows/3d-browser-game/scripts/_common.mjs";

const A = "git:" + "a".repeat(40);
const B = "git:" + "b".repeat(40);
const C = "git:" + "c".repeat(40);
const P = "git:" + "d".repeat(40);
const BRIEF_HASH = "sha256:" + "1".repeat(64);
const brief = {id:"brief-1", sha256:BRIEF_HASH, promises:["promise-loop", "promise-terminal"]};
const authority = {identity:brief.id, revision:"brief-r1", sha256:BRIEF_HASH};
const row = id => ({prompt_promise:{identity:id}, playable_evidence_ids:["increment-1"]});
const trace = (ids=["promise-loop", "promise-terminal"]) => ({kind:"traceability", id:"trace-1", artifact_commit:C, brief:authority, amendments:[], rows:ids.map(row)});
const increment = {id:"increment-1", kind:"increment", document:{id:"increment-1", kind:"increment", artifact_commit:A}};
const core = {id:"core-v", kind:"gate-verdict", artifact_commit:A, gate:"core", disposition:"pass", status:"complete", gaps:[], complaints:[], fixed_inputs:{artifact_commit:A}};
const concept = (commit=B, changed=[]) => ({id:"concept-1", kind:"concept", document:{id:"concept-1", kind:"concept", artifact_commit:commit, ...(changed.length ? {mechanics_changed:changed} : {})}});
const asset = (commit=C, changed=[]) => ({id:"asset-1", kind:"manifest", document:{id:"asset-1", kind:"asset-manifest", artifact_commit:commit, ...(changed.length ? {mechanics_changed:changed} : {})}});
const index = (entries, commit=C) => ({kind:"evidence-index", id:"index-1", artifact_commit:commit, entries});
const final = (fixed={}) => ({id:"final-v", kind:"gate-verdict", artifact_commit:C, gate:"final", disposition:"pass", status:"complete", gaps:[], complaints:[], fixed_inputs:{artifact_commit:C, accepted_core_verdict:"core-v", concept_artifacts:["concept-1"], asset_manifests:["asset-1"], ...fixed}});
const run = (id, complaints=[], lineage={}) => ({id, kind:"run-record", artifact_commit:C, brief:authority, amendments:[], complaints, lineage});
const baseEntries = (conceptCommit=B, changed=[]) => [increment, {id:"core-v",kind:"verdict",document:core}, concept(conceptCommit, changed), asset(C, changed)];
const source = async (ancestor, descendant) => true;
function input(overrides={}) {
  const prior = run("prior");
  const current = run("current", [], {relation:"integration", predecessor:"prior", predecessor_sha256:sha256(canonicalJson(prior))});
  return {gate:"final", runRecord:current, predecessorRunRecord:prior, brief, traceability:trace(), evidenceIndex:index(baseEntries()), gateVerdict:final(), sourceObservation:source, ...overrides};
}
async function main() {
  const mode = process.argv[1];
  let value;
  if (mode === "core") {
    value = await validateGateLineage({gate:"core", runRecord:run("core-run"), brief, traceability:trace(), evidenceIndex:index([increment], A), gateVerdict:core, sourceObservation:source});
  } else if (mode === "missing-core") {
    const fixture=input(); fixture.gateVerdict=final({accepted_core_verdict:undefined}); delete fixture.gateVerdict.fixed_inputs.accepted_core_verdict;
    try { value=await validateGateLineage(fixture); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "pre-core-art") {
    const fixture=input({evidenceIndex:index(baseEntries(P)), sourceObservation:async (a,d) => a.endsWith("d".repeat(40)) && d.endsWith("a".repeat(40))});
    try { value=await validateGateLineage(fixture); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "deleted") {
    const complaint={id:"complaint-1",seam:"loop",kind:"defect",cause:"bad loop",status:"accepted",evidence:["increment-1"]};
    const prior=run("prior",[complaint]); const current=run("current",[],{relation:"repair",predecessor:"prior",predecessor_sha256:sha256(canonicalJson(prior))});
    try { value=await validateGateLineage(input({runRecord:current, predecessorRunRecord:prior})); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "reopened") {
    const old={id:"complaint-1",seam:"loop",kind:"defect",cause:"bad loop",status:"fixed",evidence:["increment-1"],closure:{reason:"repaired",evidence:["increment-1"]}};
    const currentComplaint={...old,status:"open"}; const prior=run("prior",[old]); const current=run("current",[currentComplaint],{relation:"repair",predecessor:"prior",predecessor_sha256:sha256(canonicalJson(prior))});
    try { value=await validateGateLineage(input({runRecord:current, predecessorRunRecord:prior})); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "unrelated") {
    const fixture=input({sourceObservation:async () => false});
    try { value=await validateGateLineage(fixture); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "omitted-promise") {
    const fixture=input({traceability:trace(["promise-loop"])});
    try { value=await validateGateLineage(fixture); } catch(error) { value=lineageDiagnostic(error); }
  } else if (mode === "stale-reproof") {
    const fixture=input({evidenceIndex:index(baseEntries(B,["camera"])), gateVerdict:final({changed_mechanics:["camera"], affected_core_reproof:{verdict:"core-v",artifact_commit:A,changed_mechanics:["camera"]}}), coreReproof:core, sourceObservation:async (a,d) => !a.endsWith("b".repeat(40)) || !d.endsWith("a".repeat(40))});
    try { value=await validateGateLineage(fixture); } catch(error) { value=lineageDiagnostic(error); }
  } else { value=await validateGateLineage(input()); }
  console.log(JSON.stringify(value));
}
main().catch(error => { console.log(JSON.stringify(lineageDiagnostic(error))); process.exitCode=1; });
'''


def invoke(mode: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", SCRIPT, mode],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if not result.stdout.strip():
        raise AssertionError(result.stderr)
    return json.loads(result.stdout.strip().splitlines()[-1])


class GateLineageTests(unittest.TestCase):
    def test_core_acceptance_is_typed_and_traceable(self):
        result = invoke("core")
        self.assertEqual("valid", result["status"])
        self.assertEqual(2, result["traceability"]["promise_count"])

    def test_final_acceptance_proves_core_concept_and_asset_descent(self):
        result = invoke("positive")
        self.assertEqual("valid", result["status"])
        self.assertEqual(1, result["concept_count"])
        self.assertEqual(1, result["asset_manifest_count"])

    def test_missing_core_and_pre_core_art_are_rejected(self):
        self.assertEqual("missing-core-baseline", invoke("missing-core")["code"])
        self.assertEqual("unrelated-source-ancestry", invoke("pre-core-art")["code"])

    def test_unrelated_source_ancestry_is_rejected(self):
        self.assertEqual("unrelated-source-ancestry", invoke("unrelated")["code"])

    def test_prompt_coverage_is_exhaustive(self):
        self.assertEqual("omitted-prompt-promise", invoke("omitted-promise")["code"])

    def test_complaint_history_cannot_be_deleted_or_reopened(self):
        self.assertEqual("deleted-complaint", invoke("deleted")["code"])
        self.assertEqual("reopened-complaint", invoke("reopened")["code"])

    def test_changed_mechanic_requires_current_core_reproof(self):
        self.assertEqual("unrelated-source-ancestry", invoke("stale-reproof")["code"])


if __name__ == "__main__":
    unittest.main()
