# Library review prompt

The standing prompt for a full review of this library. Run it through
`orch-critique`: one trace lane per pack plus the ad-hoc lane, and one
lane per question below. Findings feed `orch-repair` or tickets. The
prompt shrinks under its own law: a question that has produced nothing
for two passes is folded or deleted; it grows only when a constitution
principle changes owner.

## Constitution

The principles this library exists to enforce. They do not change when
models improve; every review question derives from them, and every
sentence in the library must be required by one of them.

1. External evidence decides completion; a claim is worth its cited
   oracle output, and an oracle must be able to fail.
2. Independence enters every unit before final acceptance — authorship
   is part of adequacy.
3. Criteria are frozen before work; a moving target is queued scope.
4. One durable record per unit of work; results live in artifacts,
   never only in transport.
5. Star topology: one caller, one join per return; authority
   attenuates downward.
6. One owner per fact; everything else links.
7. Requests enter at the smallest structure that holds them;
   coordination is bought only when parallelism, isolation, or
   durability forces it.
8. Fixes consume causes, not findings, bounded by the frozen spec's
   license.
9. Generic bodies are domain-blind; domain data lives in pack cells.
10. Determinism over inference: a repeated deterministic step becomes
    a script.
11. The record is honest: disagreement, rationale, and contradiction
    are recorded as found, never smoothed.
12. The library learns by deletion as much as by addition; every
    sentence must be load-bearing.

## Report contract (anti-accretion)

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

## The traces — does it run?

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
constitution principle requires it; who owns it; is this the only
copy. A paraphrase beside a link is a copy. A restated definition, a
stale count, a term used off its owner's meaning, a reference loaded
at a moment it changes nothing, and prose guarding only a capability
failure a current executor no longer exhibits are all deletion
candidates; incentive guards — self-grading, laundering,
scope-widening, record-smoothing — are structural and stay. Verify
counts by listing; verify every "X checks/owns/enforces Y" claim
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
