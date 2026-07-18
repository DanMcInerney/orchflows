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
  packs, and H hosts meet in six data shapes: N+M+H mutual
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
- **Compositions are non-normative.** Worked examples rot fastest;
  outside the instruction path, rot is harmless.
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
  instantiate from compositions, the worked-example tier, so user
  reuse never mints new control flow; and an item's scope never
  exceeds the install scope that resolves its call edges, or the item
  would dangle (search is memory).

## The craft gap

Audited 2026-07-15. Each pack binds how work cuts (slicing), how done
is decided (oracles), and how review reads (lens). No pack binds what
its domain's terms mean or what good shape is at write time:

- `voice contract` is a required spec field, an `orch-draft` and
  `orch-edit` Require, a lens criterion, and a judged oracle row —
  and is defined nowhere; its scored dimensions have no owner (now
  `packs/orch-content-pack/references/craft.md`, below).
- `rigor bar` (research) is likewise undefined; `orch-tdd` tests at
  "public seams" with the term unowned.
- `orch-spec` draws a spec's nouns from `docs/vocabulary.md` "and the
  domain's own names" — a pointer with no target: vocabulary.md owns
  only the library's nouns, by design.
- Executors reference contracts only; nothing tells `orch-draft` what
  a hook is, or `orch-tdd` what shape costs its reader least.

The predicted cost: judged criteria whose terms are undefined resolve
differently in every fresh judge context, so gate verdicts churn; and
executors write to an unstated bar, so the one gate carries rework it
was designed to eliminate.

## The fix: a `craft` cell

One reference per pack, `references/craft.md`, two sections —
**Vocabulary**, the domain's terms defined once and used with exactly
that meaning in specs, tickets, lenses, and verdicts; **Shape**, the
few artifact-form principles that hold across every workspace in the
domain. Wired as a cell of
[contracts/pack-signature.md](contracts/pack-signature.md), landed as
a T0 supersession:

- `orch-spec` resolves "the domain's own names" through the stamped
  pack's craft cell — the pointer gains a target.
- Each pack's slicing lists the craft reference in its item
  extensions, so every ticket carries it and every executor reads it
  at write time, inside the delegation packet's inputs.
- Each lens grounds its criteria in craft terms instead of glossing
  them inline.

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
  tautological check, idiom); the shape section is
  the reader's cost model applied to code — exact-search names,
  one-read modules, flat application call graphs, comments only for
  the non-derivable, behavior observable at a seam.
- **Content** terms are genre-free: each names a decision every
  document makes — a tweet, a README, and a chapter all have a hook,
  a throughline, an arc, a skim layer, a landing. The voice contract
  gains its scored dimensions, which is what makes the pack's judged
  voice oracle repeatable across fresh judges.
- **Research** terms name the evidence discipline (claim, provenance,
  independence, laundering, the registers, dead ends, lane packet)
  and define the rigor bar the pack's required spec fields demand.
- **Design** terms name the rendered-interface discipline (view
  identity, capture, golden capture, token, state, affordance) and
  give the judged design-language oracle its scored dimensions; the
  shape section is the reader's cost model rendered — a token is
  one-name-per-concept for visual decisions, a view owning its states
  is locality, flat composition is breadth over depth.

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
"surface", because the hash-pinned spec contract already uses
`affected_surfaces` for touched artifacts — one word, two meanings in
the same spec was the alternative. "Standards owner" moved from code
craft to the library vocabulary when this pack became its second
consumer — one owner per fact. A new unit executor, `orch-render`,
was admitted with the pack because the unit loop differs, not merely
the artifact: red-green requires a check that can fail before code
exists, while a visual check cannot exist before the view renders —
`orch-tdd`'s discipline inverted, and one owner per judgment forbids
stretching it. The authoring order this admission followed is
[docs/pack-authoring.md](docs/pack-authoring.md).

## Why install is shaped this way

Audited 2026-07-16 on the user's decision to drop the plugin route for
`git clone` plus one installer (the plugin experiment and its decisive
evidence move to Roads not taken, below). `install.sh` (POSIX) and
`install.cmd` (Windows) resolve an interpreter — `uv run --no-project
python` → `python3` → `python`, never a bare hardcoded one — before
calling `install.py`, because anthropics/claude-code#16131 documents a
hardcoded `python3` invocation stranding Windows machines with no
`python3` on PATH; the wrapper is the fix. `install.py` auto-detects
which host halves to configure from `~/.claude` and `~/.codex`
presence rather than asking, because installed harnesses are a fact on
disk, not a preference to elicit, and it errors with guidance when
neither is present rather than completing silently having configured
nothing. The always-on instruction layer is one line the installer
appends to the user's own `CLAUDE.md` — an `@`-import pointing at
`~/.orchflows/host-block.md`, a file the installer fully owns — rather
than a block it rewrites in place inside a file it does not own,
because SuperClaude's overwrite-CLAUDE.md data-loss complaints are the
field evidence for what the latter costs users on every reinstall; the
import line is idempotent and any legacy marker block is stripped on
upgrade. Codex takes the same import-line form only where the installed
CLI resolves `@file` imports, verified once per install via a
read-only `codex debug prompt-input` probe in a scratch repo before any
`~/.codex` write; where it does not, the installer keeps the proven
marker-block upsert rather than risk an unverified import syntax.
Receipts gain `source_commit` (the git HEAD of the repo installed from)
and print previous → current commit drift on rerun because no surveyed
library in this space does install drift detection, and an installer
that silently reapplies stale content over a newer clone is a bug its
own user has no way to see.

Codex reads `~/.codex/skills` as one global, unscoped catalog whose
name and description are paid on every turn in every project
regardless of use, while a skill's body is read live from disk only at
invocation; mirroring the whole library there would tax every session
for skills most turns never invoke, so prompts stay Codex's primary
surface and only four entry points (`orch-spec`, `orch-task`,
`orch-fix`, `orch-build`) get a redirect stub — a one-line pointer at
the lib path a live read keeps at zero staleness. Project scope
collapsed to a routing-block stub because the two things a project
install used to carry beyond that were never load-bearing: friction
logging already resolves its target by walking up to `.git` rather
than depending on installer-created runtime directories, and a
project-pinned lib version was never implemented (its receipt recorded
no source commit) — so the only committable residue a project needs is
the routing block that makes its custom items discoverable in-repo; the
user-scope install still resolves every call edge (`orch-build`'s scope
law).

## Why session tracing is post-hoc

Audited 2026-07-16. `trace.py` parses committed host logs after the
fact rather than adding hooks, daemons, or a trace-write duty to every
skill, because instrumentation is machinery every body would carry
forever while a parser can decay gracefully — `schema_confidence` and
`parse_errors` price host drift instead of failing the run silently
(cheap generation; diluted attention). Model attribution stays a
routing clause on `rules/improvement.md` §3, not new tracing machinery:
`orch-self-improve` already owns clustering and routing, so reading one
more fact off a trace is cheaper than giving every skill and host a
model-logging responsibility of its own.

## Why orch-goal uses two specs

Audited 2026-07-18. A delivery's verdicts cover one frozen spec and one
run identity, so learning from delivery 1 cannot rewrite that spec
without erasing what its evidence proved. `orch-goal` instead gives the
original request, spec, and first-run evidence back to `orch-spec`, then
delivers the replacement under a new run id. A single `orch-loop` would
misname its body — delivery 2 includes re-specification — and make one
worklog claim two specs; the explicit two-run sequence preserves both
the original evidence and the revised target.

## Why the spec has two editors

Superseded 2026-07-17. A spec has exactly two editors across its
life, never a third: `orch-spec` drafts and stamps it at intake,
`orch-decompose` repairs it in place when cutting surfaces a defect —
an oracle-less criterion, a field the slicing needs that conflicts or
is missing. Every other engine only ever reads a frozen artifact.
`orch-spec` previously ran a dedicated `orch-critique` pass before
stamping to catch exactly those defects — a third reader, dispatched
as a full adversarial child, paid to find what the second reader
would find for free the moment it opened the spec to cut it.
Collapsing to two removes that redundant pass without carving out an
exception: the decomposer already has to read the spec closely enough
to cut it, so letting it correct what it finds there is the same act
as cutting, not a departure from it. The boundary holds where it
always did — a required field missing at intake is still a
caller-under-supplied rejection, and `orch-decompose` still never
widens the run's scope or branches on domain.

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
- **A generic `orch-unit` executor.** The generic unit endpoint is
  `orch-task`; executors are the domain leaves a pack binds by exact
  name, and [rules/delegation.md](rules/delegation.md) §8 forbids
  splitting a named executor into a generic shell plus a method file —
  a cut proposed once and ruled fatal. Red-green stays inside `orch-tdd`
  because proving a check can fail is cheap exactly where oracles are
  executable; its universal core — an oracle must be able to fail —
  moved to [rules/verification.md](rules/verification.md) §8, where
  every domain inherits it.
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
