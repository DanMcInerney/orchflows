# Calibration handoffs

The private calibration journal is called by benchmaker and owns its bounded
revision decisions. It reuses benchmark-qualify after changes; qualification
never calls calibration. Ordinary making tickets provide isolated, attributable
native execution and commits; independent judging tickets read fixed evidence.
The native process is the measured subject, not an Orchflows executor/profile.
No new public name, adapter, dependency or generic loop engine is introduced.

[Benchmark-quality](../standards/benchmark-quality/STANDARD.md) owns mandatory
quality. [Manifest](manifest.md), [qualification](qualification.md) and
[calibration record](calibration-record.md) own their data dictionaries. The
following are semantic payload mappings, not replacement standards.

## Input bundle

`draft` carries the full git artifact plus component locators from construction.
`qualification` carries the exact revision, typed validity, criterion verdicts,
controls/reference/attack findings and context identities. `coverage`, `rigor`,
construction `standard`, access policy, audit sample and qualification budget
are retained for each later qualification call. The helper stays inside the
benchmaker package, where benchmark-quality resolves to its orch-code base.

`target_configuration` is the same immutable object/locator across all rounds;
requested/resolved observations attach to attempts. Per-case prompt changes are
versioned benchmark inputs, not permission to change model, scaffold, effort,
tools, time limits or other pinned configuration. `calibration_policy` carries
all declared splits, cases/weights, trial count, estimator/uncertainty rule,
order/seed, retry/exclusion rules, revision and total sample budgets. Each round
has a concrete policy projection with its split, round and case ids.

`execution_mechanism` identifies native argv construction, input/output schema,
observed CLI capability/version, timeout/cleanup and independent grader interface.
`workspace` is the one integration repository for construction, attempts,
revision and freeze. `records` is its repository-relative measurement subtree,
outside `package`; `evidence_export` is a durable absolute external directory.
Candidate repositories contain only permitted visible inputs. None of these
locations alone establishes protected scorer isolation.

## Making and diagnostic payloads

| Goal | Inputs and output identity |
| --- | --- |
| `attempts` | Measured revision; concrete round policy; exact configuration; permitted scope; native/grader mechanism; remaining global launch/time/retry allocation. Returns a git evidence collection containing every launch receipt, raw transcript, prompt, candidate output or unavailable reason, grader observation, attempt row and computed summary. Every attempted event remains attributable, including infrastructure exclusions. |
| `diagnosis` | Fixed draft and attempt git artifacts through `--artifacts`; qualification findings through Context; original policy and all prior rounds. Returns findings over validity, per-case failures/uncertainty, empirical discrimination, configuration agreement, missing evidence and construct-preserving revision rationale if supported. No fresh native sample is implicit in judgment. |
| `revision` | Diagnostic findings and qualification defects; selected predeclared development change; prior draft and research/design identities; unchanged configuration/coverage/weights; remaining budget. Returns a committed changed draft and ledger entry, including new builder identities. Original findings remain locatable. |
| `requalification` | Changed or frozen revision; original coverage/rigor/standard, qualification budget, access policy, updated builder identities, predeclared audit sample and diagnostic flags. Returns benchmark-qualify's full revision-bound record, not a reused boolean from an earlier revision. |
| `finalize-records` | Every terminal branch supplies actual qualification/diagnostic/measurement returns, selected decision, immutable round identities, ledger, bounds and durable export locator. One ordinary same-repository maker commits the aggregate index, not-performed reasons and findings copies after those returns. No published summary or sealed outcome is rewritten. |
| `freeze` | VALID qualified draft and accepted development summary, original configuration and complete fixed final design. Returns the committed lifecycle-frozen package and reserved external journal locators. All final prompts/cases/seeds, references/graders, split/weights, policy and provenance are fixed by this artifact identity. |

A qualification gap may stop execution before any native attempt. A partial
record then indexes the draft, available findings, unmet inputs and an explicit
not-performed final record; it makes no live-admission claim. A failed revision
retains its preceding rounds and partial candidate evidence. A complete round
with unresolved configuration or sampling evidence retains its numeric band
observation while its calibration decision remains UNVERIFIED.

## Concrete collection boundary

Package Python uses the interpreter returned by `orchflows env workflow benchmaker`.
The existing [native collector](../scripts/native.py) `collect` accepts an argv array, fresh case
repository, visible prompt, unique output directory, fixed configuration,
explicit timeout and optional observed-configuration evidence. [grader](../scripts/grader.py)
`make_record` verifies the committed case/input/oracle binding and attaches the separately observed oracle result and trial metadata;
[record calculator](../scripts/records.py) validates and summarizes records. The measurement maker
allocates absolute locators under `evidence_export`, writes observations there,
and mirrors those exact bytes into `records` in its candidate before committing.
Commit a `.gitattributes` under the declared record subtree containing `* -text` so Git preserves raw
transcript bytes and receipt hashes across Windows checkouts.
After landing, [export.py](../scripts/export.py) with `--repository <workspace>
--revision <attempt-sha> --records <records> --destination <evidence-export>`
verifies or restores the durable export from Git. It refuses differing existing
bytes and never rewrites locators. Diagnostic judgment reads that same Git
artifact and export. Reserve unique round directories; record exports survive
candidate worktree retirement.

`scripts/admission.py collect` is the declared small Codex admission adapter,
not an arbitrary-target launcher: its argv fixes gpt-5.6-sol/low/read-only.
Other configurations use an explicitly supplied compatible execution mechanism;
an unavailable mechanism is a named gap, never a fallback to this fixture.
`scripts/admission.py summarize --input <request> --output <summary>` takes the
record-layout policy, attempt locators, criterion gaps, typed `validity`,
and no future aggregate metadata. Ledger and frozen/final locators belong only
to the aggregate index authored by the post-return finalization maker. No boolean qualification projection is accepted.

The deterministic helpers calculate and validate. The workflow driver decides
whether a qualified round can proceed, whether evidenced revision is permitted,
and whether freeze is eligible; scripts do not mint tickets or schedule rounds.

## External result index

The return identifies `development_decision` and its selected complete round,
all qualification/diagnostic findings and standard pins, `rounds`,
`revision_ledger`, `frozen_revision`, `final_record`, spend and gaps. The overall
`decision` retains required validity/evidence precedence; development and final
numeric observations remain separately named. Each ledger entry carries
pre/post revisions, reason, changed cases, strata/weights, audit identity,
complete sampling round, allocation/spend and the declared selection policy.

There is one final external record. When measurement is absent it records
`not_performed_reason`, available frozen identity, intended scope and gaps.
When present it uses the final-measurement fields in calibration-record.md,
including `evaluation_scope`, protection observations, `measurement_round` and
complete `before`/`after` file identities. Its fresh trials follow the declared
final policy. Public confirmation is labeled `public_confirmation`; unsupported
protected access is UNVERIFIED. A required protection gap can block measurement
or eligibility even when development is descriptively in band.

The final result adds final estimate/band/drift alongside the preserved
development decision. Measurement writes only to the record subtree and its external export;
changed frozen bytes are a failed integrity observation, never repaired as part
of this invocation. A new benchmark version is a separate later request.

`calibration-check` is the caller's concrete outside output check over this
index and its linked committed records. For the small disposable admission,
`scripts/admission.py probe --root <root>` checks workflow evidence;
`--require-calibrated` separately checks eligibility. Missing output, corrupt
transcript linkage, controls-only input and unexplained exclusions fail the
record probe. Synthetic event fixtures prove those checks can fail, not that a
native agent or this workflow body executed. Actual admission records name the
source commit, generated adapters, run/frame/tickets, shared standard pins,
landed artifacts/findings, outside probe exits and unexecuted branches.

Round summaries are immutable local snapshots. The finalizer combines them with
later diagnostic `development_evidence` and `terminal_gaps` in a new aggregate
index; old summaries never acquire a later revision ledger or final locator.
All terminal branches enter the finalization maker, including no-final-measurement
partials. The driver exports only its landed authored bytes.
