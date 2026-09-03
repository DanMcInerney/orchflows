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

- **A narrow waist (`contracts/`).** N workflows, M packs, and H hosts
  meet in eight data shapes: N+M+H mutual understandings instead of
  N×M×H. Each contract's field table is rendered from
  `contracts/shapes.json` and `tools/regen.py` refuses drift, because the
  reader drifts shapes helpfully — renaming a field to a nicer synonym
  reads as a favor and breaks every consumer silently (search is memory;
  cheap generation).
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
- **Authoring scope is data.** Canonical, user, and project items differ
  in landing zone and available oracles, recorded in
  [custom workflow authoring](docs/custom-workflow-authoring.md), while
  the work itself takes the ordinary smallest-first code route. An item's
  scope never exceeds the host surface that resolves its call edges, or
  the item would dangle (search is memory).

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
that closes it is each pack's `references/craft.md` — **Vocabulary**,
**Workspace**, **Spec fields** and **Lens** — defined by
[contracts/pack-signature.md](contracts/pack-signature.md) and carried
to every executor through the ticket's `pack` stamp.

Why this shape:

- **A cell, not a loose reference.** Generic skills reference domain
  facts only through the stamped pack's cells
  ([rules/composition.md](rules/composition.md) §9). A planning `orch-do`
  is generic and needs the nouns; reaching them any other way is a
  signature leak.
- **One file, not vocabulary and design separately.** A good craft
  term is a compressed principle — "skim layer" names a thing and
  instructs you to build one. The sections are consumed together at
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
  vocabulary is to judged verdicts what a rendered field table is to
  contracts — what makes independent readings converge.

Craft is bounded — a non-empty-line budget the validator enforces
(`common.py`'s `CRAFT_BUDGET`) — because
reference material that grows without consumers is exactly the
diluted-attention failure the body budgets exist to prevent.
Workspace style stays with the workspace's standards owner.

## Why the craft terms

The craft files own their text — `packs/*/references/craft.md`; this
file owns only why each list earned its lines.

- **Code** terms name the executor's discipline (seam, tracer, idiom);
  its Lens entries are the reader's cost model applied to code.
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
"surface", because the latter overloaded generic scope language.
"Standards owner" moved from code craft to the library vocabulary when
this pack became its second consumer — one owner per fact. A design render
stage was admitted with the pack because the unit
loop differs, not merely the artifact: red-green requires a check that
can fail before code exists, while a visual check cannot exist before
the view renders — the code red-green discipline is inverted, and one owner per
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

The fourth is live indirection. Codex reads `~/.codex/skills` as one
global, unscoped catalog, while a skill's body is read live from disk only at
invocation; every canonical callable therefore gets a small redirect stub to
the installed library instead of a copied body that can go stale. The former
repository-local installer path was removed because its routing block
and day-zero residue were never load-bearing: friction
logging resolves the user-scope sink through
`scripts/state_root.py` from any working directory, and a
project-pinned lib version was never implemented (its receipt recorded
no source commit). The user install resolves every call edge. Project
authoring scope remains a distinct landing zone for custom skills and
workflows under `<repo>/.orchflows`; it is not an installer scope.

## Why session tracing is post-hoc

Audited 2026-07-16. `trace.py` parses committed host logs after the
fact rather than adding hooks, daemons, or a trace-write duty to every
skill, because instrumentation is machinery every body would carry
forever while a parser can decay gracefully — `schema_confidence` and
`parse_errors` price host drift instead of failing the run silently
(cheap generation; diluted attention).

## Why custom items live in rings

Designed 2026-08-31 from an audit of this library's own scoping plus a
fifteen-system survey (Claude Code, the cross-vendor agent-skills layer,
GitHub Actions, pre-commit, VS Code, direnv/mise/nix, dbt, npm, cargo,
krew, Homebrew, Terraform, oh-my-zsh, Obsidian, Emacs dir-locals). The
audit's surprise was that this was greenfield rather than
reorganization: project scope existed for packs alone, project skills
had no reader at all, project workflows were documented in three places
and read by nothing, and `/super-research` ran entirely outside the
library through a hand-written host shim.

- **Three rings, one bundle shape, one resolver.** Every surveyed system
  that got scoping right uses one fixed, short, root-relative path per
  kind and no configurable search path; GitHub Actions goes furthest and
  forbids subdirectories. Two resolvers disagreeing about which file is
  "the pack" was a live divergence here, so the order is stated once in
  code and the bare `<dir>/packs` root that caused it is gone. The same
  `.orchflows` directory is a project ring, the home ring's custom half,
  and a publishable bundle, so nothing has to be reshaped to move
  between them.
- **The home ring is a git repository, not a config directory.** The
  sync question — "how do I get my workflow onto the next machine" —
  has a boring answer once the committed and regenerable halves are
  separated by one `.gitignore`: clone, install, sync. Friction history
  and run ledgers travel with the items, which is what makes the clone
  worth having.
- **Reference plus pin, never promotion.** GitHub spent four years on
  "make this action work everywhere" and shipped better reference syntax
  rather than a copy-it-globally command; npm's global tier is the
  survey's cautionary tale, one version for all projects and outside
  every lockfile. So `orchflows add url@pin` records a pin and
  `imports/` is regenerable from it, and there is no `promote`.
- **Trust is granted by digest, kept outside the artifact, and never
  syncs.** Every surveyed system puts the approval record in user-local
  state precisely because config directories are dotfile-synced; mise
  says it in one line, that a repository may request trust and may never
  grant it. Nix's two-step prompt — use once, or remember — is what
  makes "yes, just this once" cheap and persistence deliberate. The
  failure this closes is not hypothetical: a config file that trusted
  its own path was a real CVE, and this library's pack digest read the
  signature contract from beside the pack, so a ring could supply the
  document its own identity was taken against.
- **The seal is the lockfile.** Skill bodies said "the stamped pack
  digest" while no field carried one, so the ticket named a pack and a
  name resolves to whatever bytes are nearest. Pinning at issue and
  verifying at every later command makes the trust grant and the seal cite
  one digest: what was approved is what runs.
- **Why three dependency classes.** One "dependencies" file would have to
  answer three different questions with one lifetime. What an item's own
  scripts import is orchflows' to install, once per item, in an environment
  it can rebuild and prune. What an item needs on the machine — ffmpeg, a
  browser, an API key — orchflows must not install: installing a system tool
  is a decision about someone's machine, so `tools.txt` is declared and
  checked and nothing more, and a variable is reported by name and never
  printed. What the artifact needs — the game's three.js — is not a
  dependency of orchflows at all; it belongs to the workspace's own manifest
  and lockfile, installed by the child that is making the thing and
  committed with it, or every run would reinstall the world into a directory
  the user never asked for. Keeping them apart is what makes one environment
  per item safe: two items pinning conflicting versions is not a conflict,
  because they never share one.
- **Generated adapters are inert on purpose.** Orchflows can gate what
  enters its own prompts and tickets. It cannot gate a host's native
  loading of a repository's committed `.claude/skills/`, where a skill
  body's preprocessing runs before the model sees anything. So the
  generated bodies carry a pointer or a command and nothing executable,
  and the host-side gap is left to the host rather than papered over.

Deliberately not built: a registry or marketplace (reference plus pin is
enough; curation is a badge, not a gate), sandboxing (no surveyed system
has one), and signing (the digest is krew-style checksumming already;
real signing needs artifact hosting this library does not do).

## Why the trunk is mechanical

Reviewed 2026-08-30 across PRs #117–#136, roughly 30 session
transcripts, and 7,200+ friction records. Six recurring bug classes
turned out to be one shape: a deterministic fact or a multi-step
transaction with no mechanical owner, left to the model to reproduce
from prose. A model reproduces prose well and reproduces it *slightly
differently each time*, which is exactly the failure mode a contract
cannot catch — every individual step is defensible, and the sequence is
wrong. So each thread was answered by naming an owner in code, and the
corresponding instructions were deleted from the docs rather than kept
as fallback lore. Fallback lore is how two owners appear.

- **The LLM sequenced dispatch and return by hand.** Now `tickets.py
  dispatch` is the outbound transaction and `tickets.py land` the
  inbound one. The role→launch hop in particular was the single
  transcribed link in the system — read the host file, pick the profile
  row, type a model into the launch verb — and a mistyped model there
  killed a dispatch. Emitting a `launch` object the caller invokes
  verbatim removes the transcription, not just the mistake.
- **The per-child worktree had no creator.** `work-item.md` called
  establishment "host-owned", which meant improvised; isolation was
  recorded rather than enforced. It was the largest single friction
  cluster (341 entries over ten days). `workspace.py establish` now
  creates it, `state_root.candidate_paths` alone derives where, and an
  establishment that cannot succeed refuses the dispatch instead of
  quietly falling back to the shared tree — the fallback being how a
  packet came to carry another ticket's workspace.
- **One fact defined in N places.** Consolidation was chosen over
  synchronization on the usual grounds, but the sharper reason is that
  duplicated facts drift *silently*: nothing fails when two spellings
  disagree until something downstream branches on the difference.
- **Derived artifacts had no regeneration owner.** Each consumer was
  repaired individually as it went stale. `tools/regen.py` declares
  artifact→generator once and validate calls its check, so staleness
  fails the existing five rather than earning a sixth.
- **Refusals named no remedy.** A refusal that tells the caller nothing
  actionable is an invitation to improvise, and improvisation around a
  refusal is how runs wedged. Every such message now names a command
  that exists, and a test proves it exists.
- **Tickets carried stale values instead of derivations.** A recorded
  value is true once; a derivation is true whenever it is read.

The two-verb split also draws the honest line for this library's
central claim. `dispatch` and `land` are pure bookkeeping — replayable,
refusing before side effects. What is left to judgment is what the work
is and whether it is good. Ask what happens if the model becomes
perfect: a perfect model still cannot make a non-atomic sequence
atomic, and still cannot know which of two spellings of a path is the
one the join will grade. That is the test for what belongs in code.

- **The receipt handshake, superseded 2026-08-30.** The accept step
  (`dispatch-receive`, the `dispatch-receipt` record, the inline packet
  form, and their refusal family) policed the packet-less-fork class, and
  PR #89 had already closed that class structurally at the installer, at
  the one point in a fork's load path a packet can never reach. What was
  left cost the accept phase 29 s to 6 m 16 s per child, mostly
  refusal-retry over the receiver's own directory, and stored 50–59 KB of
  duplicated handshake per gate ticket. It fails the same test: a perfect
  model still cannot make the accept atomic, but it also never needed to —
  the child's first filed record already proves the same identity the
  receipt echoed back, because `result` validates
  `(dispatch_id, assignment_seal, --by)` on every write. The evidence and
  the full disposition are `research/subagent-simplification-design-2026-08-30.md`.

- **The packet as a wire object, superseded 2026-08-31.** Of its
  twenty-one fields, the two a child could not obtain any other way —
  where its assignment is, and which tree to stand in — were the two the
  wire did not carry, so twelve of twelve launches were composed by hand
  against `rules/delegation.md`'s "improvises neither", and those hand
  prompts were the dominant defect source of the runs that produced this
  design. The wire is gone. `dispatch` emits one launch whose prompt is
  the whole child-facing surface and whose every fact is machine-filled,
  which is the same test again: a perfect model still cannot know which
  spelling of an absolute path the establishment recorded, and it should
  never have been asked to type one. What the prompt refuses to say is as
  load-bearing as what it says — it names no skill for the child to invoke
  and no pack for it to resolve, because a fork arriving without a prompt
  can obey neither.
- **Structure only where a machine reads it.** The ticket used to
  over-prescribe in both directions at once. On the way out it forbade the
  planner from naming a file, a check, or a step — a law written against a
  planner that guesses, which also bound the planner that had just spent an
  hour reading the code. On the way back it required a child to sort its work
  into five headings no consumer read. The evidence that broke both is the
  same evidence: the freehand briefs that built stages A through C violated
  the first wholesale — evidence-anchored prescribed deletions, named checks,
  definition-of-done commands, 1,300 words — and their unstructured returns
  beat the sectioned ones, because honest exit codes and deferrals-with-
  reasons are what a reader needs and no taxonomy produces them. So `Details`
  is free-form and unbounded, and `Report` is one channel. The rule that
  replaces both is narrow: prescribe as hard as investigation earned, carry
  the evidence and the escape hatch with every prescription, and keep
  structure only where something mechanical reads it. The return side had
  one such exception — a JSON findings file the join bound into the review
  ledger — and it retired too once the join stopped adjudicating: `Report`
  is the one channel without exception now. The test is the amnesia test
  again: a perfect model still cannot guess the file you already read, and
  still gains nothing from being told which heading to file a fact under.

## Why two callables, frames, and prose

Designed 2026-08-31 from the seven investigations of 2026-08-30, the ring
work, and a super-research dogfood run that logged fourteen frictions. The
finding underneath all three: workflows and skills were never two kinds. A
workflow is a skill whose prose calls other skills, down to the small set
that does real work — composition is functions calling functions, and the
interpreter is whichever agent the user is already talking to. Everything
the library had built to be that interpreter was machinery it did not need
to own.

- **Two callables, not four.** The four verbs were four entry points into
  one pack's craft. A pack is read three ways and always was; what the tier
  actually needs is one callable that makes something and one that reads
  something, each naming which craft sections its call is for. Freezing a
  root is a `do` whose artifact is a sealed root, which is why the intake
  verb and the cutter both retire into it rather than into each other.
- **The ticket tree is the call stack.** One move buys durability for
  arbitrary depth: every invocation opens a ticket, and a `parent` link
  makes the tree mirror the calls. A resumed orchestrator reads the tree; it
  does not reconstruct a stack it never persisted. Frames carry no lease,
  because their driver is a session rather than a dispatched child, and a
  stale frame is shown with its age for a human to judge — unknown never
  decays into idle.
- **The journal is working memory, not insurance.** The design's first draft
  called journaling a cheap habit over a re-derivation floor. That was the
  sharpest thing the Fable review overturned: the common failure of a prose
  driver is not death but degradation — a compaction mid-workflow
  paraphrases the very lines the parent was trusted to relay, and resume
  never fires because nothing died. The incumbent's stateless ready/frontier
  reads were accidentally load-bearing against exactly this. So waves are
  pull-based for the living driver too: re-read the journal and the
  children's states, decide, append.
- **Typed lines, because the relay is the seam.** The one-line contract was
  Git-shaped and the pack roster is not, so the artifact line is typed per
  adapter and a judge returns its findings path the same way. What is
  verbatim survives a compaction; what is prose does not.
- **Judge-or-say-why at a multi-child close.** Composition-invisibility is
  an information-access problem — no member can see the whole from its own
  seat — so it survives the perfect-model test and earns one mechanical
  check. A frame closing over two or more `do` children refuses without a
  judging child or an `unjudged: <reason>` line, which converts a silent
  under-review into an auditable decision.
- **What this bought by deletion.** The loop lane and its marker grammar,
  the template/instantiate/placeholder layer and entry kinds, the reader's
  workflow-summary manifest, the stamp/validate/seal command parade as
  separate public commands, admission's graph-shape checks, and the gate
  choreography with its lens ordering. Each fails the same test the trunk
  review set: a perfect model still cannot make a sequence atomic or know
  which spelling a join will grade — but it can perfectly well write a
  loop, and none of that machinery was buying anything else. Critique and
  repair survive as prose over `judge` and `do`; compare-and-swap sealing
  survives inside the callable and frame minting commands. Sunk cost stated
  plainly: parts of the loop-lane PRs and the instantiate half of the ring
  work are deleted by this design.
- **A callable keeps its lease; a frame gets none.** The review called the
  lease borderline under perfect models. It is not a capability mechanism:
  it arbitrates writer contention on dispatchable work, which no model
  quality removes. Frames are singular and session-bound, so displaying
  their age suffices; callables are dispatchable by anyone holding the
  sink, so the lease is the arbiter.
- **Why sheets and applied skills.** Two verbs left two real gaps: craft one
  assignment wants and no other, and a method one call runs. Both failed as
  verbs — a third verb is a new entry point into the same pack — and both
  fail as packs, since a house style or one client's report shape is not a
  new domain. They pass the perfect-model test from the other side: a
  perfect model still cannot know which style this caller wants or which
  bytes a judge will be graded against, and the fix is data the caller
  stamps, not procedure the model executes. So a sheet is craft pinned by
  digest on one ticket and read by exactly that ticket's maker and judge,
  and an applied skill is a method pinned the same way inside the kernel
  contract that still owns Require, Never and Return. Both are stamped and
  neither is called, which is why neither is a call edge and neither needed
  a verb. The cost is one more thing a ticket can pin, and the mitigation is
  that a sheet only tightens: where it loosens the craft, the craft wins and
  the judge reports the sheet.
- **Packs bind per call, not per run.** Callables never share a workspace —
  each adapter owns its own callable's world — so the one-pack-per-run law
  and the adapter-compatibility worry behind it both dissolve. One callable
  is one pack is one artifact; two domains in one deliverable are two
  callables and a handoff. Frames carry no pack, because a journal is not
  craft-governed work.

Eyes open on the costs: parent-mediated handoffs can still drift, and the
verbatim machine line is the whole mitigation; the composition vantage is
opt-in past the two-child floor; and a workflow imported from someone else's
ring executes as orchestrator reasoning, which is why the containment
default is to drive it in a spawned frame agent.

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
- **A benchmarks pack, and an executor for oracle-bearing artifacts.**
  Both refused 2026-08-08, against the signature's admission line.
  No new oracle class: discrimination runs a check and compares an exit
  code, which is `deterministic` — a class is a property of how a
  verdict is produced, not of what it is about. No new workspace
  semantics either, and the reason is stronger than "one consumer":
  the library already defines visibility constraints in four places — typed check
  verdicts, candidate-blind evaluation, research lanes, and canary withheld
  anchors — in their pack contracts, never in a `workspace` cell. Protected evidence policy names
  the held-back files. The
  paired executor was refused with it: its claimed ground — that an
  oracle's counterexample is constructible only after the oracle exists
  — is false, because a counterexample derives from the behavior, which
  the ticket fixes before work starts. That is an ordinary red-green
  slice against a fixture per
  [rules/verification.md](rules/verification.md) §8, which is where the
  bullet above already put this. Reversal needs a deliverable whose
  visibility partition cannot be expressed through an existing skill or
  pack contract.
- **A new-cell appetite.** The signature grows only when a generic
  skill needs judgment no cell promises, read strictly. Craft was
  admitted because the planning noun source had no owner — not
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
