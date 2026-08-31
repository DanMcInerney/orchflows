# Orchflows rings — where custom skills, packs, and workflows live

2026-08-31. Research report for the custom-item scoping design. Status:
PROPOSED — the design below is what Stage F implements and the
super-research rebuild dogfoods. Evidence: an internal audit of orchflows'
scoping machinery at `main` (`eaf26f66`) and the installed tree
(`e2dffb0a`), plus a fifteen-system external survey (Claude Code, the
cross-vendor agent-skills layer, GitHub Actions, pre-commit, VS Code,
direnv/mise/nix, dbt, npm, cargo, krew, Homebrew, Terraform, oh-my-zsh,
Obsidian, Emacs dir-locals, plus git/ESLint/Jupyter as bonus precedents).
This file moves into `research/` with Stage F.

---

## 1. The question

A user should be able to build something like super-research — a custom
workflow with skills and maybe a pack — while standing in their own
project, or in no project at all; run it from Claude, Codex, or Grok; sync
it across machines the way they can already sync their friction logs by
making `~/.orchflows` a git repo; and share it with a team or the world.
Where does everything live, what works where, and what keeps a cloned
stranger's repo from injecting into their agents?

## 2. What orchflows has today (audit, condensed)

The audit's surprises reframe the problem — this is greenfield, not
reorganization:

- **Project scope exists for packs only.** `packs_support._roots()`
  searches project `.orchflows/packs` → user `~/.orchflows/packs` →
  canonical → lib (`scripts/packs_support.py:141-157`). Project
  **skills have no reader at all** — stage 1 deleted
  `tickets_sequence.py`, the only code that ever resolved
  `.orchflows/skills/`. Project **workflows are documented in three
  places and read by nothing**: `instantiate` takes a bare filesystem
  path, no name resolution, no host adapter, no slash command.
- **`/super-research` runs entirely outside orchflows** — a hand-written
  `.claude/skills/super-research/SKILL.md` shim with an `@`-include and
  Claude Code's own `disable-model-invocation` flag. Nothing in the
  installer knows it exists.
- **There is no digest pinning.** Skill bodies say "stamped pack digest,"
  but no ticket field carries one; the assignment seal covers the pack's
  *name string* (`scripts/tickets_generations.py:11-14`), and
  `cells_for(digest)` is a lookup that re-derives digests to find a pack —
  never a verification against a stored expectation. The digest machinery
  itself is good (cells + every referenced file's bytes + the signature
  contract); the durable expectation is the missing half.
- **Two resolvers disagree.** `tickets_adapters._candidate_roots()` checks
  bare `<dir>/packs` *before* `<dir>/.orchflows/packs` for every ancestor
  (`scripts/tickets_adapters.py:73-83`) — a different order than
  `packs_support`. Admission and execution can read different files as
  "the pack."
- **The injection surface is open.** A project pack shadows a canonical
  name first-hit-wins-silently; the `orch-` reservation is a doc sentence
  with no enforcement; and a project can ship its own
  `contracts/pack-signature.md` whose bytes feed *its own pack's digest*
  (`packs_support.py:344-346`). The craft document — read whole into
  worker and checker prompts — carries no trust step of any kind.
- **The installer is user-scope only** and already renders per-host
  adapters for every library skill *and* workflow: `~/.claude/skills/`,
  Codex prompts+skills, Grok skills (`installer/planning.py:253-306`).
  `~/.orchflows/packs` and `~/.orchflows/skills` are named as resolution
  roots in code but never created.
- **The state sink separates projects by field, never by directory**
  (`rules/visibility.md:35-36`; `runs/<run>/run.json` carries the project
  binding) — which is exactly what a syncable home repo needs.

## 3. What the field teaches (survey, the load-bearing subset)

Patterns repeating across three or more of the fifteen systems:

- **P1 — one fixed, short, root-relative path per kind; never a
  configurable search path.** GitHub Actions goes furthest and *forbids*
  subdirectories under `.github/workflows`.
- **P2 — the trust record always lives outside the artifact it
  authorizes, in user-local state, and is never shareable.** mise puts
  approvals in `~/.local/state` *specifically because* `~/.config` is
  dotfile-synced and approvals must not be portable. "A repo may request
  trust; it may never grant it."
- **P3 — "works anywhere" is solved by reference-plus-pin, never by
  copying into a global directory.** GitHub spent four years on the
  problem and shipped better reference syntax (`$/`), not a promotion
  command. npm's global tier is the survey's cautionary tale (FM-9:
  outside the lockfile, one version for all projects).
- **P5 — data merges; code shadows.** And **P6 — a hard floor of names
  extensions can never capture** (kubectl built-ins, cargo aliases, dbt
  `ref`/`source`) — noting FM-11: kubectl's floor is *silent*, which is
  its own failure mode.
- **P8 — the gate is on capability, not identity.** mise's "safe"
  declarative-only configs need no trust; Emacs auto-applies values whose
  `safe-local-variable` predicate passes; VS Code's scope enum makes
  dangerous keys structurally unreachable from workspace config
  ("warned… and then always ignored" — enforcement, not prompting).
- **P12 — the lockfile is the real pin; the manifest is only an intent.**
  Terraform, which deliberately doesn't lock modules, is the
  counterexample that proves it.
- **Nix's two-step prompt** is the single strongest UX finding: *"allow
  this setting?"* then *"permanently mark as trusted?"* — separating
  act-now from remember-forever so "yes, once" is cheap and persistence
  is deliberate.

Failure modes that directly constrain this design:

- **FM-1**: repo-supplied config as an RCE vector, in every ecosystem
  that reads it — including Claude Code itself (CVE-2025-59536: project
  hooks executed *before* the startup trust prompt).
- **FM-2**: **the policy that decides whether to trust a file must never
  be readable from that file** (mise CVE-2026-35533: a repo shipping
  `trusted_config_paths = ["/"]` in its own config trusted itself). Our
  pack-signature self-supply hole is this exact class.
- **FM-3**: trust fatigue has two opposite causes — VS Code's
  too-coarse blocking prompt trains click-through; direnv's
  re-block-on-every-edit trains blanket whitelisting. mise's defaults
  (path-keyed, auto-trust on intentful commands, declarative-exempt) are
  the explicit concession to both.
- **FM-4**: mutable tags are not pins (`tj-actions`: 23,000+ repos;
  SHA-pinned consumers unaffected).
- **FM-6**: the agent-skill load path can bypass the model entirely —
  `` !`cmd` `` preprocessing in a skill body runs *before* Claude sees
  anything, and "a cloned repo can bring skills into a trusted Claude
  Code session even if the developer never installed a skill from a
  marketplace." Claude Code's workspace trust does not gate skill bodies
  or `allowed-tools` at all.
- **FM-13**: discoverability degrades silently under scale (Claude's
  skill listing drops the least-used descriptions to fit a 1% context
  budget).

## 4. The design

### 4.1 Three rings, one bundle shape

```
R0  ~/.orchflows/lib/          installed library — cattle, regenerated
R1  ~/.orchflows/              the HOME ring — your git repo
      skills/  packs/  workflows/     committed: your custom items
      state/                          committed: friction, run ledgers
      imports.lock                    committed: pinned external bundles
      imports/<name>/                 GITIGNORED: the pinned clones
      lib/  lib.version               lib gitignored; version pin committed
      trust.json                      GITIGNORED: never syncs (P2)
R2  <project>/.orchflows/      the PROJECT ring — rides the project's repo
      skills/  packs/  workflows/
```

**One bundle shape everywhere**: an `.orchflows/` directory with
`skills/`, `packs/`, `workflows/` is the same format as a project ring, as
the home ring's custom half, and as a standalone published workflow repo
(a repo that *is* a bundle, nothing else — the Homebrew-tap /
pre-commit-hooks-repo pattern). The repo's own `example-workflows/` are
each a valid bundle you can copy out.

**The home repo answers the sync question**: new machine =
`git clone` your home repo + `install.py` (reads `lib.version`,
regenerates `lib/`) + `orchflows sync` (restores `imports/` from
`imports.lock`, renders host adapters). Your workflows, skills, packs,
*and your whole friction history* arrive together. The committed/
regenerable boundary is the one law: nothing custom is ever written into
`lib/`, and nothing regenerable is ever committed.

### 4.2 One resolver

One resolution function for every kind (skill, pack, workflow), used by
dispatch, admission, check, `instantiate`, and the inventory command —
killing the two-resolver divergence (S3). Order: **project → home
(own, then imports) → lib.** Fixed paths only (P1): bare `<dir>/packs`
stops being a root. Collisions:

- **`orch-*` is a mechanically reserved floor** (P6): a ring item with a
  reserved name is refused *loudly* at resolution — never kubectl's
  silent never-runs (FM-11).
- Non-reserved collisions: nearest ring wins, and the resolver prints a
  one-line shadow notice naming both paths.

`instantiate` gains name resolution through the same chain (today it
takes only a bare path), which is what makes a project workflow invocable
by name — and what the host adapters point at.

### 4.3 Trust: digest-granted, ring-scoped, never portable

- **R0 and R1 are inherently trusted** — you installed one and authored
  the other (the same reasoning Claude Code applies to user-scope memory
  imports).
- **R2 gates on first use, keyed by bundle digest** (content, not path —
  Jupyter/direnv-shaped, but per-bundle so ordinary edits to *other*
  files never re-prompt). The prompt is Nix's two-step: use once (no
  record) or remember (record `{bundle, digest}` in `trust.json`). A
  digest change re-prompts, naming which files changed. The ledger is
  gitignored: **trust never syncs** (P2, mise's reasoning verbatim).
- **Imports are trusted by the act of adding them** (pre-commit's model:
  consent is the install, not the clone): `orchflows add <url>@<rev>`
  records the pin in `imports.lock`; only a pin change re-prompts. Never
  a branch name (FM-4) — the add command refuses mutable refs the way
  pre-commit warns on them.
- **FM-2 closes**: the digest's signature bytes always come from lib's
  `contracts/pack-signature.md`, never pack-relative; and no
  trust/resolution policy is ever read from an R2 file.
- **Pinning becomes real** (closes S2): the ticket seal records
  `pack_digest` at slice time; dispatch and check verify the resolved
  pack against it. The trust grant and the seal cite the same digest, so
  what you approved is what runs (P12 — the seal is the lockfile).
- **Honest boundary**: orchflows can gate what enters *its* prompts and
  tickets. It cannot gate Claude Code's native loading of a repo's
  committed `.claude/skills/` (FM-6 — no workspace-trust coverage
  there). The design keeps generated adapters inert (frontmatter + a
  pointer command; no preprocessing constructs) and leaves the host-side
  gap to the host.

### 4.4 Hosts: extend the renderer that already exists

The installer already renders every lib skill and workflow into
per-host adapters (Claude `~/.claude/skills/`, Codex, Grok). Stage F
extends the same pipeline to rings:

- **Home-ring items** render into user-scope host surfaces on
  `orchflows sync` — available everywhere, on all three hosts, exactly
  like lib items today.
- **Project-ring items** render into the *project's* host surfaces
  (`<repo>/.claude/skills/`, `<repo>/.agents/skills` for the
  Codex/cross-vendor convergence) — committed, so they travel with the
  repo, and cd-scoped by the hosts' own native behavior. This replaces
  the hand-written super-research shim with a generated one.
- A workflow's adapter carries the `instantiate <name>` route (the
  existing workflow-adapter pattern, now name-resolved through the one
  resolver).

### 4.5 UX flows, end to end

- **Create**: `orchflows new {skill|pack|workflow} <name>` scaffolds into
  the project ring when you stand in a project, else the home ring —
  write-target follows mise's rule (the shared file, never a local
  overlay). The self-hosted route stays: an orchflows run can author a
  pack (the factory pattern the docs already describe).
- **Use everywhere (yours)**: put it in the home ring; git push; every
  machine follows.
- **Share with a team**: commit it to the project ring; teammates get it
  on clone, behind the first-use trust prompt.
- **Publish**: make the bundle its own repo; consumers
  `orchflows add url@rev`.
- **Discover**: `orchflows list` — the one resolver's view of *here*:
  every resolvable item, its ring, shadow notices, trust state. Same
  code path as runtime resolution (krew's inventory-vs-runtime split is
  the anti-pattern).

### 4.6 In the library repo

`example-workflows/` → **`example-workflows/`**, and the user-facing term
becomes **workflow** (vocabulary owns the rename; "composition" was
library jargon). The existing workflows (evolve, drift-canary,
self-improve, benchmaker, browser-game, renovate, skill-tournament) move
there as the inspiration gallery, each a copy-out-able bundle.
super-research lands there *and* in the home ring — the dual proof.

## 5. Stage F implementation scope

1. One resolver module for all kinds + rings; kill
   `tickets_adapters._candidate_roots`'s divergent order; `orch-*`
   reservation enforced; shadow notices.
2. `pack_digest` recorded at seal, verified at dispatch and check;
   signature bytes always lib's.
3. Trust ledger + first-use prompt (two-step) for R2 bundles;
   `trust.json` gitignored; no policy read from R2.
4. Home-ring layout: installer creates `skills/ packs/ workflows/`,
   writes `lib.version` and the home `.gitignore` (lib/, imports/,
   trust.json, runtime/, ui/, tmp/); `orchflows sync` renders ring
   adapters for all three hosts; `orchflows add` + `imports.lock`.
5. `instantiate <name>` resolution; `orchflows new` scaffolds;
   `orchflows list`.
6. `example-workflows/` → `example-workflows/` + vocabulary rename; generated
   project-ring adapter replaces the super-research shim.
7. Sweep the stale scope docs the audit flagged
   (`custom-workflow-authoring.md`, `documentation.md` factory table,
   vocabulary's dead `.orchflows/workflows/` landing zone,
   `scope-edges.json` orphan).

**Deliberately deferred**: any registry/marketplace (P3 says reference-
plus-pin is enough; curation is a badge, not a gate), sandboxing (no
surveyed system has one; mitigations are out-of-band), signing (krew-
style checksums via the digest already; real signing needs artifact
hosting we don't do).

## 6. Open questions

1. **State retention in the home repo.** Friction and run ledgers are
   the sync value; the tickets sink accumulates ~100KB+ per gate ticket.
   Commit `state/friction/` + `state/runs/` but gitignore
   `state/tickets/` with an archival prune command? Or commit everything
   and prune by policy?
2. **Trust prompt surface.** The prompt fires inside script commands
   (dispatch/instantiate refuse with the remedy naming
   `orchflows trust <bundle>`), since orchflows has no interactive UI of
   its own. Acceptable, or should the host adapter carry the prompt?
3. **Codex/Grok project-ring surfaces.** `.agents/skills` is the
   cross-vendor convergence; Grok's discovery mechanism is the least
   settled (and Grok writes inside our managed markers — a known
   defect). Ship Claude+Codex first and let Grok follow?
