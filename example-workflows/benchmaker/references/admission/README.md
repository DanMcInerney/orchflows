# Admission machine interfaces

These scripts are package-owned boundaries called by the calibration maker and
root's outside probe. They do not launch Orchflows tickets or decide revisions.
The request in [live-admission.md](../live-admission.md) owns the live experiment.
`prepare` emits inputs only. Construction still authors the three starters,
references, deterministic checks, and confirmation variants; qualification still
requires independent contexts. No candidate solutions ship in this fixture.

Run scripts with the interpreter from `orchflows env workflow benchmaker`.
All paths in JSON evidence are absolute. Store evidence outside the benchmark
package so measurements do not change its git identity.

1. `admission.py prepare --root ABSENT_ABSOLUTE_DIRECTORY` emits `request.md`,
   policy inputs, submission schema, and empty source/product/attempts/evidence
   directories. Resolve the unavailable CLI/instruction/capability inputs before
   sealing. Confirm CLI help/version. Fresh candidate repositories contain only
   their visible starter and prompt; initialize git separately before collection.
2. `admission.py collect --repository CASE_REPO --schema SCHEMA --prompt PROMPT
   --configuration CONFIG_JSON --output ABSENT_ATTEMPT_DIRECTORY` invokes the
   fixed native argv in the request, with a 90-second default timeout. It stores
   raw stdout/stderr, prompt, extracted source and `launch.json`. `--executable`
   selects the observed native executable; no shell or safety bypass is used.
   Optional `--configuration-observation JSON` supplies independently observed
   `configuration` and an `evidence_locator`; configuration must equal the target
   object and both observation and source artifact are integrity-bound. This
   input cannot be an inference from requested flags.
3. `grader.py --receipt LAUNCH_JSON --checks CHECKS_JSON --identity IDENTITY_JSON`
   executes the output independently and writes `grader.json` and `attempt.json`.
   Identity has `case_id`, `split`, `round`, `trial`, `target_configuration`,
   `benchmark_revision`, `candidate_kind`. Checks JSON is `{"checks":[...]}`;
   each check has `args` and exactly one of `expected` or `raises` (exception
   class name), optionally `no_mutation: true`. JSON-compatible `solve(*args)`
   APIs are supported, including nested lists, tuples normalized to lists, and
   exceptions. This is outcome testing, not a source-style check.
4. `admission.py summarize --input INPUT_JSON --output SUMMARY_JSON` reads
   `policy`, absolute `attempts` locators, `criterion_gaps`, `instrument_valid`,
   `revision_ledger`, optional `frozen_revision` and `final_record`. Policy keys
   are `case_ids`, `split`, `round`, `trials_per_case`, `target_configuration`,
   optional normalized case `weights`, `band`, `infrastructure_retry_budget`,
   and `require_resolved_configuration` (default true). Explicit false makes
   unavailable provider metadata an `optional_gaps` entry, not a required gap;
   declare this rigor choice before attempts.
   Default weights are equal cases; repeated trials never become new cases.
5. `admission.py probe --root ROOT` reads `evidence/admission.json` and prints
   workflow admission and calibrated eligibility separately. Add
   `--require-calibrated` for an eligibility exit (2 for an admitted partial
   result). Missing/corrupt evidence exits 1. A declared resolved-configuration
   gap yields UNVERIFIED; an omitted or mismatched configuration fails.

`evidence/admission.json` is authored by the runtime executor, never prepare:

```json
{
  "benchmark_manifest": "absolute product benchmark manifest JSON",
  "component_locators": {
    "benchmark-construct": "absolute installed private SKILL.md",
    "benchmark-qualify": "absolute installed private SKILL.md",
    "benchmark-calibrate": "absolute installed private SKILL.md",
    "benchmark-quality": "absolute installed private STANDARD.md",
    "benchmark-evidence": "absolute installed private STANDARD.md"
  },
  "runtime": {
    "run": "actual run", "frame": "actual frame", "tickets": ["actual ticket"],
    "standard_pins": {"maker": ["same pinned standards"], "judge": ["same pinned standards"]},
    "artifacts": ["landed artifact line"], "findings": ["independent findings line"],
    "package_revision": "fixed source commit",
    "journal_locators": ["absolute actual runtime ticket/frame journals"]
  },
  "qualification": {
    "instrument_valid": true,
    "audits": [{"case_id": "case", "benchmark_revision": "commit",
      "builder": "context identity", "auditor": "different context identity",
      "reference_outcome": "PASS", "inert_outcome": "FAIL", "near_miss_outcome": "FAIL",
      "evidence_locator": "absolute audit evidence file"}]
  },
  "rounds": [{"policy": {}, "attempts": ["absolute attempt.json"],
    "summary": "absolute summary.json", "criterion_gaps": ["explicit required gaps"]}],
  "revision_ledger": [], "frozen_revision": null, "final_record": null,
  "decision": "UNVERIFIED"
}
```

Each round's policy fully declares its cases/trials/configuration. All attempted
rounds are retained. If final measurement occurred, `final_record` names JSON
with `before` and `after` maps of absolute frozen paths to SHA-256. The probe
checks equality, the complete file inventory below the manifest directory,
current bytes, and the measured manifest against its git blob identity. The
source checkout HEAD must equal runtime package_revision, all measured revisions
must resolve in product git, and journal text must carry declared runtime ids
and pins. Development round ids are consecutive from zero and correspond to
the revision ledger. A final record also carries `frozen_revision`,
`measurement_round` (the exact entry already included in rounds), and
`evaluation_scope` (protected_final, public_confirmation, or development). A
protected_final additionally needs `protection` with status VERIFIED, mechanism
and an existing adversarial `probe_locator`; the outside reviewer evaluates
that evidence, since file existence alone cannot prove access isolation. These hashes protect attempt linkage and
freeze observations; the benchmark's version identity remains git.

Limits: subprocess separation is fault containment, not read isolation. The
candidate and grader can access host files under host permissions. A protected
final claim requires separately observed access controls and attack evidence.
Native JSON does not attest the full requested configuration: collection records
that unresolved fact instead of inventing a model version. Required missing observations remain gaps; explicitly optional metadata is
reported separately. A supplied independent configuration observation can
satisfy the declared contract, but cannot invent provider metadata. Native event fixtures in
unit tests are harness controls, never live-admission evidence. The probe checks
stored provenance structure and deterministic results; the outside root also
observes actual emitted tickets and launches to establish execution provenance.
