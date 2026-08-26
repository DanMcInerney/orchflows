# Design rationale

`ARCHITECTURE.md` owns where things live; `docs/vocabulary.md` owns
what words mean; `rules/` owns law. This file owns why. It is
non-normative: where rationale and a rule disagree, the rule wins and
this file is stale.

The library has one significant reader and writer: a language model
operating through a file-tool harness — read, search, spawn. Every
structural choice below traces to an operating constraint of that
reader. Human legibility is welcome; it is never the design driver.

## The reader's constraints

- **Amnesia.** Every context starts empty and dies without heirs.
  Nothing persists except files. A convention that lives only in a
  prior context is already lost.
- **Metered, parallel-shallow reading.** Reading costs per file. One
  turn can read many files at once but can follow a dependency chain
  only one hop per turn: breadth parallelizes, depth serializes. Deep
  indirection is the most expensive shape a repository can take.
- **Search is memory.** The reader finds things by exact-match search,
  not recollection. A concept with two names doubles every search and
  halves the confidence that all uses were found; one name shared by
  two concepts is worse.
- **Cheap generation, scarce verification.** The reader produces
  plausible artifacts far faster than anything can check them. The
  binding resource of any run is trustworthy verdicts, not output.
- **Diluted attention.** Instruction-following degrades with every
  word that is not load-bearing; a 200-line contract is followed worse
  than a 25-line one even when the extra lines are true.
- **Shared blind spots.** Executor, reviewer, and judge are the same
  weights. Independence must be manufactured structurally — fresh
  contexts, blind lanes, external oracles — never assumed.

## Structure → constraint

- **A narrow, hash-pinned waist (`contracts/`).** N workflows, M
  packs, and H hosts meet in five data shapes: N+M+H mutual
  understandings instead of N×M×H. Hash-pinned because the reader
  drifts shapes helpfully — renaming a field to a nicer synonym reads
  as a favor and breaks every consumer silently; the pin turns drift
  into a failing test (search is memory; cheap generation).
- **Skills wear function anatomy.** Require / procedure / Never /
  Return gives a contract the reader can pattern-match instead of
  prose it must infer; body budgets with overflow to `references/`
  keep the always-paid cost small and the rarely-needed detail
  off the bill (diluted attention; metered reading).
- **Kernel skills call no skill.** Call depth is the serial cost; a
  frozen floor of primitives bounds every chain statically, and a
  child can load one file and have its whole world (metered reading).
- **Packs are data, never control flow.** The domain fork must not
  live in workflow bodies, or there are M diverging copies of every
  workflow. One generic body reading domain facts through cells means
  a domain is added by writing data, not by editing control flow
  (search is memory; diluted attention).
- **Compositions are the stdlib.** A named workflow is a data file —
  steps, edges, invariants, done check — admitted like any skill and
  invocable by name (see "Why the named tier is ticket-set templates"
  below).
- **Tickets and worklogs are markdown on disk.** Files are the only
  memory every context shares and the only store the reader can
  search with native tools. An external tracker is state an amnesiac
  must re-authenticate to and cannot grep (amnesia; search is memory).
- **Runtime state is data, never an instruction source.** The reader
  follows imperative text wherever it encounters it; directories that
  children write to are quarantined as data by law, or every child
  output is an injection vector (shared blind spots).
- **Iteration is fresh-context replay from a worklog.** A long
  context accumulates stale beliefs and self-agreement; killing it
  and restarting from frozen goal plus worklog is checkpoint/restore
  that sheds contamination (amnesia, used as a feature).
- **Lanes and judges are blind.** Convergence between independent
  lanes is evidence; convergence between lanes that shared a draft is
  one opinion laundered into consensus (shared blind spots).
- **The executor's claim is never green.** The cheapest artifact to
  produce is the claim of success; verdicts come only from named
  oracles, and `oracle_class` states exactly how much a verdict can
  be trusted (cheap generation).
- **One gate.** Review passes multiply rework and stall runs; a
  single bounded review-fix pass forces quality to be specified
  before writing rather than discovered after. That trade is safe
  only if executors receive the quality bar at write time — which is
  what the craft cell below exists to carry.
- **The friction law.** The reader cannot reconstruct its failures
  after the fact; an observation logged at the moment of friction is
  the only faithful record, so the log's fidelity ceilings the
  library's improvement rate (amnesia).
- **Scope is data (`orch-build`).** Canonical, user, and project items
  differ only in landing zone and available oracles, so one build
  judgment reads those facts from a table — the same move that keeps
  domains in packs and hosts in the installer. Custom workflows
  instantiate from compositions, the named-workflow tier, so user
  reuse never mints new control flow; and an item's scope never
  exceeds the install scope that resolves its call edges, or the item
  would dangle (search is memory).

## Why the named tier is ticket-set templates

Since 2026-08-16 (P4 of the ticket-set redesign; the 2026-08-06
two-entrypoints spec was the intermediate step, and git history owns
both migrations). Routing once enumerated named "shapes of done" whose
bodies were mostly sequencing, and every recurring shape grew the
routing table — the one surface every session pays for on every
request. The replacement:

- **The routing table stays fixed while the named tier grows.** Three
  branches — answer, ticket, fix — and one closed rule: everything else
  runs only when named. Recurring shapes accumulate as templates under
  `compositions/`, never in the dispatch prose (diluted attention: the
  always-paid cost never grows).
- **A template is tickets, not a second grammar.** A demoted pattern's
  law rides its stubs' `excluded_actions` and `## Completion test`; the
  combinators are the ticket graph's own — a `depends_on` edge, disjoint
  parallel stubs, a loop stub — so `tickets.py instantiate` writes a run
  and `orch-frontier` drains it with no engine, contract or step file to
  keep in step with the ticket contract (cheap generation: the gate is
  the same graded ticket shape every other item has).
- **The envelope closes the algebra.** Every dispatchable unit returns
  one envelope — status, result identity, verification — so a
  predecessor's result identity is a successor's evidence with no
  per-pair glue (search is memory: one return shape, one name).

Its open decisions closed as: ticket sets over a fixed `seq` engine,
proven on the `fix` fixture; Claude keeps all skill adapters — measured
2026-08-16, the verdict and its caveat in benchmarks/routing/README.md;
the delegation contract merged into `work-item.md`; orch-delegate (the
skill) deleted; the domain instances and `orch-loop` kept.

## Why documentation is designed this way

Every session is a team death. A program is a theory its builders hold
(Naur), and under agents the theory dies at each context boundary — so
documentation is not a description for a reader with time. It is the
theory-rehydration procedure for a reader with a token budget, run
cold, by role, hundreds of times: the at-rest half of the context
window, engineered like one — loaded selectively by role and event,
budgeted, and graded by machines. Bloat is not a style problem; it
lowers task success. The law that follows is
[docs/documentation.md](docs/documentation.md).

## Why a `craft` cell

Since 2026-07-15. Each pack bound how work cuts, how done is decided,
and how review reads; none bound what its domain's terms mean or what
good shape is at write time. Undefined judged terms resolve differently
in every fresh judge context, so gate verdicts churn, and executors
write to an unstated bar the one gate then pays for in rework. The cell
that closes it is each pack's `references/craft.md` — **Vocabulary** — defined by
[contracts/pack-signature.md](contracts/pack-signature.md) and carried
to every executor through the ticket's `pack` stamp.

Why this shape:

- **A cell, not a loose reference.** Generic skills reference domain
  facts only through the stamped pack's cells
  ([rules/composition.md](rules/composition.md) §9). `orch-spec` is
  generic and needs the nouns; reaching them any other way is a
  signature leak.
- **One file, not vocabulary and design separately.** A good craft
  term is a compressed principle — "skim layer" names a thing and
  instructs you to build one. The two halves are consumed together at
  write and review time; splitting doubles every child's reads.
- **Per pack, not central.** `docs/vocabulary.md` is the library's
  own namespace and stays domain-free; a central domain glossary
  charges every child for all domains to get one. Domain terms belong
  to the domain's one owner.
- **Write-time, not review-time.** With one gate there is no
  iterative style convergence; the cheapest place to apply a quality
  bar is the first draft. A sixty-line read per child is cheaper than
  one gate rework cycle.
- **It stabilizes judged oracles.** Deterministic oracles need no
  vocabulary — an exit code means the same thing in every context.
  Judged oracles are rubrics executed by fresh instances of the same
  weights: an undefined dimension is re-invented per judge. Craft
  vocabulary is to judged verdicts what hash pins are to contracts —
  what makes independent readings converge.

Craft is bounded — a 60-non-empty-line budget the validator enforces,
and a closed consumer test that makes an unconsumed term a defect,
both owned by the cell's definition in
[contracts/pack-signature.md](contracts/pack-signature.md) — because
reference material that grows without consumers is exactly the
diluted-attention failure the body budgets exist to prevent.
Workspace style stays with the workspace's standards owner.

## Why the craft terms

The craft files own their text — `packs/*/references/craft.md`; this
file owns only why each list earned its lines.

- **Code** terms name the executor's discipline (seam, tracer,
  tautological check, idiom); the shape section is the reader's cost
  model applied to code.
- **Content** terms are genre-free: each names a decision every
  document makes — a tweet, a README, and a chapter all have a hook,
  a throughline, an arc, a skim layer, a landing. The voice contract
  gains its scored dimensions, which is what makes the pack's judged
  voice oracle repeatable across fresh judges.
- **Research** terms name the evidence discipline (claim, provenance,
  independence, laundering, gaps, evidence packet); the rigor bar
  itself is one of the pack's required spec fields, stated per run.
- **Design** terms name the rendered-interface discipline (view
  identity, capture, golden capture, token, state, affordance) and
  give the judged design-language oracle its scored dimensions.

## Why the design pack

Admitted 2026-07-16 on the signature's admission rule, via workspace
semantics: the identity algebra is new. Design acceptance is
undecidable from source text, so what a verdict covers and a golden
capture pins is view × breakpoint × state at a revision — a spec's
enumerated states are first-class identities, not files, and no
revision-plus-path identity can name "the nav, focused, at 375px".
Writes still land on path sets; what changed is what coverage and
evidence mean. The domain follows the oracle, not the file type: a
run whose acceptance reads source and runs tests stamps code even
when it edits stylesheets; a run whose acceptance is decided against
captures stamps design. Design is also where craft pays most — its
acceptance is judged-heavy, exactly the oracle class where an
undefined term makes fresh verdicts churn. What never admits a pack
is "different principles" or "different libraries" alone: framework
specifics (component libraries, utility-CSS idioms) stay with the
workspace's standards owner, as genre stays out of content craft.

Choices on the record: the renderable unit is a **view**, not a
"surface", because the root ticket already carries affected surfaces as
`write_scope` ([contracts/work-item.md](contracts/work-item.md), Root
ticket) — one word, two meanings in one ticket was the alternative.
"Standards owner" moved from code craft to the library vocabulary when
this pack became its second consumer — one owner per fact. A new unit
executor, `orch-render`, was admitted with the pack because the unit
loop differs, not merely the artifact: red-green requires a check that
can fail before code exists, while a visual check cannot exist before
the view renders — `orch-tdd`'s discipline inverted, and one owner per
judgment forbids stretching it. The authoring order this admission
followed is [docs/pack-authoring.md](docs/pack-authoring.md).

## Why install is shaped this way

Audited 2026-07-16 on the user's decision to drop the plugin route for
`git clone` plus one installer (the plugin experiment and its decisive
evidence move to Roads not taken, below). `install.py`'s own docstring
owns what the installer does; these are the four reasons it does it
that way. The root wrappers resolve an
interpreter rather than hardcoding one because
anthropics/claude-code#16131 documents a hardcoded `python3` invocation
stranding Windows machines with no `python3` on PATH. The always-on
layer is an appended `@`-import to a file the installer fully owns,
never a block rewritten inside a file it does not, because
SuperClaude's overwrite-CLAUDE.md data-loss complaints price the
latter on every reinstall. Receipts carry `source_commit` and print
drift on rerun because no surveyed library in this space detects
install drift, and an installer that silently reapplies stale content
over a newer clone is a bug its own user cannot see.

The fourth is the catalog tax. Codex reads `~/.codex/skills` as one
global, unscoped catalog whose
name and description are paid on every turn in every project
regardless of use, while a skill's body is read live from disk only at
invocation; mirroring the whole library there would tax every session
for skills most turns never invoke, so prompts stay Codex's primary
surface and only the four entry points `install.py` names get a
redirect stub — a one-line pointer at
the lib path a live read keeps at zero staleness. The former
repository-local installer path was removed because its routing block
and day-zero residue were never load-bearing: friction
logging resolves the user-scope sink through
`scripts/state_root.py` from any working directory, and a
project-pinned lib version was never implemented (its receipt recorded
no source commit). The user install resolves every call edge. Project
build scope remains a distinct `orch-build` landing zone for custom
skills and compositions under `<repo>/.orchflows`; it is not an
installer scope.

## Why session tracing is post-hoc

Audited 2026-07-16. `trace.py` parses committed host logs after the
fact rather than adding hooks, daemons, or a trace-write duty to every
skill, because instrumentation is machinery every body would carry
forever while a parser can decay gracefully — `schema_confidence` and
`parse_errors` price host drift instead of failing the run silently
(cheap generation; diluted attention).

## Roads not taken

- **A central domain glossary in `docs/`** — wrong owner, and an
  all-domains context charge for every single-domain child.
- **Separate vocabulary and design references per pack** — two reads
  for halves of one thing.
- **Craft as a skill** — craft has no procedure and no Return; it is
  data, and pack purity exists to keep judgment-free domain data out
  of control flow.
- **Workspace style guides** — the standards owner already exists and
  outranks; restating it would create the library's first two-owner
  fact.
- **A generic orch-unit executor.** The generic unit endpoint is
  `orch-frontier` over one ticket; executors are the domain leaves a
  pack binds by exact
  name, and [rules/delegation.md](rules/delegation.md) §8 forbids
  splitting a named executor into a generic shell plus a method file —
  a cut proposed once and ruled fatal. Red-green stays inside `orch-tdd`
  because proving a check can fail is cheap exactly where oracles are
  executable; its universal core — an oracle must be able to fail —
  moved to [rules/verification.md](rules/verification.md) §8, where
  every domain inherits it.
- **A benchmarks pack, and an executor for oracle-bearing artifacts.**
  Both refused 2026-08-08, against the signature's admission line.
  No new oracle class: discrimination runs a check and compares an exit
  code, which is `deterministic` — a class is a property of how a
  verdict is produced, not of what it is about. No new workspace
  semantics either, and the reason is stronger than "one consumer":
  the library already partitions visibility in four places — `orch-verify`'s
  blind scoring, `orch-eval-design`'s candidate-blindness, research lanes,
  `orch-fixture`'s withheld anchors — and enforces every one at the
  dispatch layer that [contracts/work-item.md](contracts/work-item.md#dispatch)
  owns, through `inputs` and `authority`, never in a `workspace` cell.
  Protected evidence is that construct with the held-back files named. The
  paired executor was refused with it: its claimed ground — that an
  oracle's counterexample is constructible only after the oracle exists
  — is false, because a counterexample derives from the behavior, which
  the ticket fixes before work starts. That is an ordinary red-green
  slice against a fixture per
  [rules/verification.md](rules/verification.md) §8, which is where the
  bullet above already put this. Reversal needs a deliverable whose
  visibility partition cannot be expressed through a dispatch's
  `authority` and `inputs`.
- **A new-cell appetite.** The signature grows only when a generic
  skill needs judgment no cell promises, read strictly. Craft was
  admitted because `orch-spec`'s noun source had no owner — not
  because more reference material seemed nice. The next cell must
  clear the same bar.
- **A generated Claude Code plugin.** Audited 2026-07-16 against a
  plugin prototype (`claude --debug-file`): plugins silently drop
  nested `skills/` directories and never expand `@`-includes in a
  plugin skill body — the two mechanisms every canonical package's
  `SKILL.md` depends on — forcing a flattened, include-expanded tree
  regenerated from canonical `skills/`: a second representation of
  every skill, the one-owner-per-fact failure this library exists to
  avoid. Upstream marketplace install/update paths carry stale-cache
  bugs of their own. Plugin `settings.json` supports only
  `agent`/`subagentStatusLine`, and plugin agents require the
  `orchflows:` namespace on `subagent_type`, so the installer script
  would still be needed to write concurrency settings and bare-named
  role agents regardless — a plugin would add a second distribution
  path without removing the need for the first. A Codex-side plugin
  would carry only skills and pay the identical per-turn catalog tax
  the redirect stubs already pay at zero build cost, so it would not
  even solve Codex's half of the problem.
