# Lens keying successors

Frozen root for the run that closes what run 20260902T024320Z's two judges
reported (findings files under `research/run-notes/reviews/20260902T024320Z-B1.6-*`
and `-B1.7-*`) and the three friction entries its children filed. Every fact
this document asserts about the tree is carried as the command that derived
it, with the count that command returned at freeze (tip 346a7bae); an
executor re-runs the command rather than trusting the count.

## Units

Independent seams, one `do` each under `orch-code-pack`, isolation required,
on branch `claude/orchestrator-subagent-analysis-758331`. Shared files are
named per unit so the join can predict its conflicts:
`tests/serial_compat_manifest.json` (every unit that adds a test) and
`tests/test_dispatch_launch.py` (S3 removes three classes, S4 adds one case
inside `LandTest`, which S3 leaves in place).

### S1 — the `blocking` law gets one owner, and `### root` gets a provenance clause

Findings F2 and T5. `git grep -n blocking -- packs contracts rules skills docs`
returns 2 lines, both `packs/orch-code-pack/references/craft.md` (the `### git`
entry's closing paragraph). That paragraph fuses library law (when a finding
is `blocking: true`, and that non-blocking findings are reported, never
repaired in the same run) with code taste (a shape finding never outranks a
correctness finding).

- Move the library half to `rules/verification.md`, the owner of the
  critique/repair boundary (444 words at freeze, `wc -w`), as one numbered
  clause in its existing style; it applies to every pack.
- Leave the code craft its weighting sentence. Give each of the other four
  crafts' deliverable entries one weighting sentence of their own — the
  smallest true one is "weigh in listed order" — so a judge under any pack
  has both the law (rule) and the weight (craft). Craft non-empty-line
  budget is 130; the largest craft is 100 (`grep -c . packs/*/references/craft.md`).
- Add to the code craft's `### root`, beside "A pointer to the standards
  owner": a claim the root makes about the state of the target tree — which
  module carries a behavior, which checks read a name it retires, what a
  constant is — is carried as the command that derives it, never as a
  recalled fact; and the intake question "What must keep working" is
  answered by that command's output. Two sentences. Evidence: T1 and T2 of
  the B1.7 findings file are both instances; `### cut` already carries the
  rule for line counts.
- If `skills/kernel/orch-judge/SKILL.md`'s budget (300 words; 169 at freeze)
  holds it, one clause pointing at the rule for what `blocking` means.

### S2 — two discriminators say what their docstrings say

Findings F4 and F5, both "make the code state the rule the prose states".

- `scripts/tickets_assignment.py` `lens_key` reads Context `- artifact: `
  lines before `makes`, with no executor gate; a planning `do` whose
  Context cites a predecessor identity would be sent to the adapter's kind.
  Gate the artifact-lines branch on
  `EXECUTOR_REGISTRY[_executor_of(loaded)]["files_findings"]` (the module
  already imports `_executor_of`); a `do` falls through to `makes`, then the
  adapter. Test with a `do` whose Context carries an artifact line: key is
  `makes`. Put the test beside `lens_key`'s existing coverage in
  `tests/test_dispatch_launch.py`'s `LensKeyPromptTest` only if S3 has not
  moved it; otherwise, and preferably, in a small new module
  `tests/test_lens_key.py` so the seam is not shared with S3.
- `tools/validate_support/common.py` `CRAFT_OPTIONAL_SECTIONS` is read by
  nothing: `git grep -n CRAFT_OPTIONAL_SECTIONS -- '*.py'` returns 2 lines,
  the definition and `__all__`. `validate_craft_sections` in
  `tools/validate_support/names.py` closes the `###` keys both ways but
  leaves the `##` roster open. Add the third loop: a `##` heading not in
  mandatory, optional or retired is an error naming it. Tests in
  `tests/test_validator_cases/corpus_and_surfaces.py` beside the existing
  craft-section cases, with the can-fail reading recorded.

### S3 — the launch composer grows sideways

Finding F6. `wc -l scripts/tickets_dispatch_launch.py tests/test_dispatch_launch.py`
returns 604 and 938; `tools/check_source_sizes.py` reports warnings=38 and
names both. The seam: the prompt is line groups sharing only the assignment
dict.

- Move `_command`, `_identity_line`, `_lane_lines`, `_reading_lines`,
  `_files_findings`, `_craft_lines`, `_friction_lines`, `_return_lines`,
  `ARTIFACT_LINE_FORMS`, `FINDINGS_LINE` to `scripts/tickets_dispatch_launch_lines.py`
  (the `tickets_` prefix is auto-discovered by `installer/inventory.py`
  `SCRIPT_SUPPORT_PREFIXES`; keep the `if __package__:` flat-import
  fallback every scripts module carries). `launch_prompt`, host binding,
  `launch_spec`, `precheck` stay.
- Import surface, derived: `git grep -ln tickets_dispatch_launch -- '*.py'`
  returns `scripts/tickets_assignment.py`, `scripts/tickets_dispatch_facade.py`
  and six test modules; the one symbol that moves and is imported elsewhere
  is `ARTIFACT_LINE_FORMS` (`tests/test_ticket_callables.py`); point that
  import at the new owner rather than re-exporting.
- Split the tests along the same seam: `ReturnLineConditionalTest`,
  `IdentityLineTest`, `LensKeyPromptTest` move to
  `tests/test_dispatch_launch_lines.py`; `LaunchResolutionTest`,
  `DispatchLaunchTest`, `LandTest` stay in place and unmoved (S4 adds a case
  inside `LandTest`). Regenerate the manifest; the moved
  `LensKeyPromptTest.setUp`/`.minted` mutation owners re-key to the new
  module and keep their `selected-module-boundary` ruling.
- Observable: both files under 500 physical lines; `check_source_sizes`
  warnings fall to 36; `ARCHITECTURE.md` names the new module where it
  names the composer (`git grep -n tickets_dispatch_launch ARCHITECTURE.md`,
  1 line at freeze).

### S4 — two refusals arrive before their side effect, naming the rule

Friction entries from B1.4's landing and from B1.6/B1.7's closes.

- `scripts/tickets_outcome.py` refuses a closing note containing a line
  that starts with `## ` or the writer attribution, saying only "contains a
  reserved heading or attribution". Name the first offending line (its
  1-based line number and first 60 characters) and the rule ("lines may
  not begin with `## ` or `### Written by `; `###` and deeper are fine").
  Test beside the existing outcome-envelope tests.
- `scripts/tickets_land.py` `_land_transaction` integrates the candidate
  (`_integrate_workspace`, a merge commit on the workspace branch) before
  discovering the ticket carries no `done` predicate and no `--status`, then
  refuses; run 20260902T024320Z B1.4 shows the merge commit 2e502dc3 created
  by a refused call. Resolve `tickets_done`'s "driver grades it" refusal
  before the first side effect, with the same message. Test inside
  `tests/test_dispatch_launch.py`'s `LandTest`, which S3 leaves in place.

### S5 — a second `--pin` in one change is idempotent

Friction from B1.2. `tools/validate_support/lint.py` `validate_pin_supersessions`
compares the working-tree `tests/pins.json` digest against the current
contract; after one `--pin`, the recorded digest is an intermediate that was
never committed, `_historical_contract_text` finds no such blob, and the
check demands a T0 supersession record citing a digest no reader will see.
When the recorded digest has no committed history, compare against the
digest recorded in `git show HEAD:tests/pins.json` for that contract and
require the record to cite that committed digest. Tests in
`tests/test_validate_cases/` beside the existing supersession cases: a
re-pin after an uncommitted pin passes when a record cites the committed
digest; the committed-digest requirement itself still bites.

## Out of scope

The bare `python` Windows stub (host environment, noted in AGENTS.md); a
tree-wide retired-heading lint (F1's class remedy: it would fire on the T0
supersession records that must keep quoting the names); any new artifact
kind.

## Acceptance for the whole

`python tools/run_required.py --no-cache` green at the joined tip;
`git grep -n blocking -- packs` returns one weighting sentence per craft
and no law; `check_source_sizes` warnings 36; a `land` with no predicate and
no `--status` leaves no merge commit; `validate.py --pin` twice in one
change with one supersession record exits 0 both times.
