# Layered workflow authoring: implementation root

Planning artifact, not new library law.

Dispatch: B1:d1
Assignment seal: sha256:37a22f7d7022286602cdb68d123d08cd9e33b8006b312ca38ee70ccd83260532
Assigned name: B1

## Goal

Make workflow authors reliably choose and compose existing primitives, standards,
and reusable workflows before inventing new orchestration. Deliver concise
guidance at the authoring reading surface and a default-shipped, named
orch-build-workflow entry point that uses existing lower-level orchestration.
Specificity should tighten quality through standard narrowing and supply semantic
inputs to reusable calls. Public workflows should mostly delegate to meaningful
contracts beneath them where such contracts exist. Do not require a fixed number
of layers, a wrapper for every step, or a new standard for every invocation.

The resulting authoring workflow must create or improve one scoped workflow
package, admit it statically, invoke its actual body in a disposable project, and
return its fixed artifact identity with observed runtime evidence and declared
gaps. A successful static check alone must never be reported as proof that prose
branches executed.

Target: C:/Users/danhm/.codex/worktrees/7fe4/orchflows-public.
Examined baseline: 9736e28e76672db43c95eed18f0d1df2a9baf6b6.
Standards owner: AGENTS.md in that repository.
Authoring owner: docs/custom-workflow-authoring.md in that repository;
carry C:/Users/danhm/.orchflows/lib/docs/custom-workflow-authoring.md in
every governed ticket's Context. Apply orch-code and the authoring lens.

## Decision and evidence

Choose documentation plus a small dogfooded builder. Documentation alone would
make the relationships explicit but would leave the repeated authoring,
independent review, runtime admission, and delivery sequence to each caller.
The existing checkpointed-build contract already owns most of that sequence.
The builder earns its own name through the workflow-authoring contract and
evidence it supplies, not by copying that sequence. This is a bounded product
improvement authorized by the request, not a claim of measured reliability gain.

Preserve current core architecture. Its public seams already provide the required
composition and narrowing behavior:

- rules/composition.md §§12–16 supplies tightening chains, recurrence, placement,
  private helpers, package identity, and ordinary public calls.
- contracts/standard.md supplies ordered broad-to-narrow expansion, shared-base
  deduplication, orthogonal guidance, and contradiction as standard-defect.
- docs/custom-workflow-authoring.md supplies package layout and scope changes,
  deterministic calls, callable admission, and real disposable-project evidence.
- skills/workflows/checkpointed-build/SKILL.md supplies planning, independent
  making waves, joined-tip judgment, bounded repair, and external close.

The gap is the connection between these existing decisions at the authoring
surface: authors are told the individual rules but lack a compact, explicit
selection procedure connecting reusable contracts, call graph, narrowing, and
the task-specific public entry point. The current guide's Procedure starts
step-by-step authoring; improve that owner instead of adding another guide.

Read-surface evidence: templates/host-block.md already requires the authoring
pointer in Context for skill/workflow/standard/contract/router work.
docs/documentation.md §4 gives executors their ticket and Context, and
scripts/tickets_dispatch_launch_lines.py emits the pinned standard reading
instructions. There is no need to load the complete authoring guide into every
ordinary maker or enlarge the router with the full method. Improve its existing
trigger/pointer only if necessary for discoverability; authoring children must
receive the pointer through decomposition.

The source browser-game example is an intake/evidence/checkpoint workflow with
domain criteria and specialized schema references. It is not the installed
3d-browser-game workflow. It is useful evidence of the kind of task-specific
entry point under discussion, but rewriting or running a whole game production
workflow is not necessary to prove this authoring improvement.

### Re-derivation commands

Run from the target checkout at the examined revision, or repeat against the
actual implementation baseline. These commands carry the tree-state claims;
the prose above does not substitute for rerunning them after a baseline change.

- git rev-parse HEAD
- git status --short
- Get-Content -Raw rules/composition.md
- Get-Content -Raw contracts/standard.md
- Get-Content -Raw docs/custom-workflow-authoring.md
- Get-Content -Raw docs/standard-authoring.md
- Get-Content -Raw docs/documentation.md
- Get-Content -Raw templates/host-block.md
- Get-Content -Raw skills/workflows/checkpointed-build/SKILL.md
- Get-Content -Raw example-workflows/browser-game/SKILL.md
- rg --files skills example-workflows --glob SKILL.md
- rg -n 'def discover_workflow_skills|WORKFLOW_LIB_DIRS|manual' installer/packages.py
- rg -n 'discover_workflow_skills|codex_skills|by_name|lib_copies' installer/planning.py
- rg -n 'replaced wholesale|rmtree|_remove_stale' installer/application.py
- rg --files tests --glob '*workflow*' --glob '*standard*' --glob '*install*'
- rg -n 'narrows|private|package|cycle' tests --glob '*.py' --max-count 5

All Python checks use the host's verified interpreter, not bare python.

## Implementation scope

1. Improve the authoring owner's selection procedure and authoring lens. Require
   a concise inventory of relevant existing contracts before adding one. Choose
   the smallest useful primitive or workflow; extract a repeated orchestration
   when the recurrence/journal rule earns it; leave an ordinary sentence inline.
   Explain public versus private placement and require actual callers or an
   independent journal reason for a new reusable boundary. State that layers
   organize responsibility, not a depth quota. Separate workflow control flow,
   applied methods, and quality guidance. Use the standard contract's meanings
   rather than duplicating its chain rules.

2. Add orch-build-workflow as a canonical, manual-only workflow. Prefer
   example-workflows/orch-build-workflow/SKILL.md: authoring workflows is a
   particular artifact domain, whereas skills/workflows is domain-blind.
   Both existing homes ship by default through the same discovery and adapters.
   Its semantic inputs must settle the request, git source workspace, intended
   landing scope, applicable authoring owner, bound, and observable admission.
   Reuse checkpointed-build by its ordinary public name with concrete inputs,
   including making and judging standards, narrowing list, and external probe.
   The builder owns authoring-specific requirements and evidence; it does not
   restate checkpointed-build's plan/waves/judge/repair mechanics. It must not
   turn every straightforward authoring edit into mandatory extra children.

3. Add a compact, globally resolvable orch-workflow-authoring standard narrowing
   orch-code, if needed to carry the builder's recurring artifact-quality bar.
   This is justified for maker/judge parity across multiple authoring runs.
   Its guidance checks contract reuse, meaningful boundaries, quality tightening,
   evidence coverage, scope preservation, and declared runtime gaps. It owns
   no control flow, executable helpers, or Return protocol; cite canonical
   composition and authoring owners rather than copying them. Global canonical
   placement is intentional: checkpointed-build is another public package and
   starts its own scope, so it cannot resolve the builder's private standard
   merely because its caller could. Do not alter package scoping to solve this.

4. Add only the deterministic regression coverage needed for the new shipped
   name, adapter behavior, valid standard expansion, and the observable runtime
   fixture. Prefer existing test owners and generated inventories. A small
   fixture/probe may live inside the builder package; do not create a universal
   workflow DSL, abstract runner, fixture schema, or new ticket fields.
   Documentation may link an executable fixture for worked detail rather than
   adding an inert multi-level example agents cannot run.

5. Dogfood the candidate builder by invoking its actual named body on a small
   workflow-authoring request in a disposable project. Use meaningful existing
   composition, such as producing a specialized public workflow that calls
   checkpointed-build with a tightening standard and a tiny file-producing
   artifact whose output is independently observable. The fixture must exercise
   standard carriage across the public-call scope change. Choose enough work to
   demonstrate the real seam; do not manufacture private helpers just to make
   the call graph deeper. Independent judgment and external done must observe
   the actual produced artifact. Record the run/frame/ticket identities,
   standard chain pins, final commit, findings, command exits, and gaps.

The implementer may simplify the proposed file split if equivalent evidence
shows a smaller result. A core change needs a reproduced public-seam failure,
a targeted repair, and its own review; architectural permission is not a reason
to widen the task speculatively.

## Acceptance and failure seams

- Authoring intake: the changed reading surface reaches both planner and
  authoring maker via existing Context carriage. An uncomplicated task may stay
  shallow; useful reuse is chosen before a new contract is added. Independent
  authoring review assesses behavior, not sentence matching.
- Distribution: ordinary library discovery includes the builder exactly once;
  supported host adapters remain manual-only and roleless for it; the narrowing
  has no invocation adapter. Private fixture resources do not become global
  skill names. No hand-maintained name allowlist or duplicate body is added.
- Quality: stamping the authoring narrowing expands to orch-code then the
  narrowing, with the same pins for maker and judge. Missing names fail openly;
  contradictory narrowing guidance is a standard defect, not permission to
  weaken the base. Reuse existing chain tests where they already cover behavior.
- Runtime: a real emitted launch is executed and its outcome lands; the output
  closes on an external probe. Remove or corrupt the expected fixture output
  and observe the probe fail, then use the real valid result to observe success.
  Do not claim a synthetic ticket test is a live agent invocation.
- Failure: unresolved semantic inputs remain explicit; no invented project
  scope, hidden dependency, or fake artifact. Missing tools or unavailable live
  admission return the partial artifact and evidence gap. Failed static
  admission, unresolved names, stale package pins, and a blocked judge prevent
  a success claim. Existing repair bounds and partial-result contracts remain.
- Compatibility: existing package scope, trust, role binding, standard ordering,
  and public Require/Return contracts remain valid. No mass game refactor,
  routing policy replacement, automatic workflow invocation, or installed-only
  gallery deletion is included.

These are observable outcomes, not frozen internal test commands. The executor
derives scoped checks from the final change. The gate runs AGENTS.md's five
required checks to completion at the joined identity (run_required.py
--no-cache), and records the live admission separately. Existing green tests
need a can-fail observation only where they are used as decisive new evidence;
do not duplicate already sufficient coverage.

## Installation boundary

installer/packages.py discovers both workflow homes automatically.
installer/planning.py creates by-name and supported host surfaces for those
discoveries. installer/application.py replaces the entire library and removes
stale tracked host adapters. A new canonical item therefore ordinarily needs
no installer architecture change.

The parent reports installed receipt source 74676fcd6e7a0cafd73fef121dd7c58b34d9a768,
which differs from this planning baseline. The parent also reports installed
3d-browser-game absent from this source inventory. Treat the receipt identity
as parent-provided evidence until directly re-derived at installation. Do not
reinstall this older/divergent source tree blindly. At delivery, root compares
the installed receipt and its source tree with the checked candidate, forms a
clean integration source preserving accepted installed additions, checks that
identity, then installs it with the accepted-source assertion and reads the
receipt. If that source cannot be reconstructed without guessing, report the
installation gap while retaining the checked artifact. Direct lib edits and
untracked overlays are not a substitute for accepted source.

## Planning limitations

No implementation, test run, real workflow admission, or installation occurred
in this planning ticket. Source reads establish available contracts and
distribution behavior; they do not prove the proposed builder works. The
post-change live run is required evidence, and long-term reliability remains
unmeasured. No child was delegated by this planner.
