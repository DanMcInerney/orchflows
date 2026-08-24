# Library review prompt

The standing prompt for a full review of this library. Run it through
`orch-critique`: one path-walk lane per pack plus the ad-hoc lane, and one
lane per question below. Findings feed `orch-repair` or tickets. The
prompt shrinks under its own law: a question that has produced nothing
for two passes is folded or deleted; it grows only when a constitution
principle changes owner. A project reuses everything below its
constitution with its own constitution in that slot — the review
factory of [documentation.md](documentation.md) §7.

## Constitution

The principles this library exists to enforce. They do not change when
models improve; every review question derives from them, and every
sentence in the library must be required by one of them.

1. Completion is decided by evidence from outside the executing
   context that could have failed.
2. Criteria are frozen before work; a moving target is queued scope.
3. One durable, honest record per unit: results live in artifacts,
   never only in transport, and disagreement, rationale, and
   contradiction are recorded as found, never smoothed.
4. Star topology: one caller, one join per return; authority
   attenuates downward.
5. One owner per fact; everything else links.
6. Coordination is bought only when parallelism, isolation, or
   durability forces it.
7. Fixes consume causes, not findings, bounded by the frozen spec's
   license.
8. Machinery is domain-blind; a domain enters as data, never as
   control flow.
9. Determinism over inference: a repeated deterministic step becomes
   a script.
10. The library learns by deletion as much as by addition; every
    sentence must be load-bearing.
11. A guard against a model limitation is scaffolding and expires with
    the limitation; a guard against incentives is permanent. The test
    is whether a perfect executor would still need it.

## Report contract (anti-accretion)

- A report lands at the repository root as `REVIEW-<date>.md`, a second
  report on one date taking a `-<topic>` suffix — an evidence record no
  reading-order row loads, cited by identity, excluded from the link
  check, deleted once its successor's header records what landed.
- The header states: law-text line count (rules/ + contracts/ + skill
  bodies), its delta since the last pass, and validator and test
  state.
- Findings are emitted only as root-cause threads — one owner, one
  change-set, member evidence attached with file:line — never an
  undeduplicated enumeration.
- Every thread names its remedy from the ordered set: delete > merge >
  reword (net-zero or fewer lines) > move > add. `add` is lawful only
  as a producer gap — a live consumer breaks without it — and must
  name the constitution principle that requires it.
- The report states the net line delta of applying every thread; a
  net-positive report defends each addition individually.
- Every pass nominates its five safest deletions independent of any
  defect, each with the fixture ablation that would prove it safe.
- No fixes; a lane with nothing to report says so in one line.

## The path walks — does it run?

One realistic request per pack, plus one through the ad-hoc lane
(single ticket, the checker path, and an ad-hoc set). Walk the exact
live path hop by hop, carrying the artifacts as concrete data checked
against their contracts. A hop is a finding when a consumer reads what
no producer wrote, two skills claim one step, an artifact satisfies
its contract's letter but not the consumer's need, or the path needs
knowledge the session would never load. Trace the off-nominal exits: a
failing oracle, and an excluded action → handoff → resume. Every
failure routes to a named skill or a verdict; anything that silently
degrades is a finding — this library has no fallback tier.

## Minimality and ownership — is every sentence required?

For each sentence of rules, contracts, and skill text: which
constitution principle requires it; who owns it; is this the only copy
(`rules/visibility.md` §3). A paraphrase beside a link is a copy. A
restated definition, a stale count, a term used off its owner's meaning,
and a reference loaded at a moment it changes nothing are deletion
candidates. So is a capability guard — prose protecting only against a
model limitation a current executor no longer exhibits; an incentive
guard — self-grading, laundering, scope-widening, record-smoothing —
protects against a standing incentive no executor outgrows and stays.
Verify counts by listing; verify every "X checks/owns/enforces Y" claim
against X's source.

## Adversarial — can it be gamed?

For each guard, construct the cheapest way a well-meaning executor
could satisfy its letter while defeating its principle: a self-graded
green, a laundered verdict, a widened fix, a smoothed record, an
oracle that cannot fail, a blind spot between two owners. Then update
the standing inventory of invariants neither validator nor tests
check — where review is the only enforcement, the report says so.

Close with the meta-analysis: the threads' connecting causes and the
single simplifying move that closes the most threads at once.
