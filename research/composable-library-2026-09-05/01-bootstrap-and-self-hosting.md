# 1. Bootstrap and self-hosting

Status: proposed. This is the only stage allowed to prepare the library for self-hosted implementation of the next stage.

## Dependencies

Current main at a7f19004d595fa09ab1aeda685f70002af2388fd, the installed library at the same source identity, and the canonical owner docs/custom-workflow-authoring.md. The implementation ticket is an orch-code git ticket. Do not depend on stage 2 syntax, a new ticket schema, or a host that is not detected and probed.

## Goal

An accepted stage 1 commit can implement stage 2 through a reusable implement-spec workflow using the currently legal tickets.py frame-open, do, judge, result, dispatch-outcome, frame-close, install.py --accepted-source, and orchflows sync commands. The handoff leaves a known-good predecessor available and does not change a live run's installed substrate.

## Current-code evidence

The current callable usage in scripts/tickets_mint.py accepts repeatable --standard, goal/details files, parent, skill, done, makes, isolation, bound, workspace, and host. It does not accept --profile at this layer; stage 1 examples therefore use no imaginary profile flag. scripts/tickets_dispatch_launch.py already resolves role profiles against hosts/*.json, but scripts/tickets_dispatch_launch_lines.py currently emits the same universal “Call the Skill tool” entry for every host, so host-native entry semantics remain an adapter seam. scripts/workspace.py and the ticket land/join modules already own candidate establishment, retirement, stale-attempt protection, and integration. install.py --accepted-source exists and receipt.json records the source commit.

Two boundaries are not implied by those capabilities. installer/packages.py:accepted_source_commit checks only that the supplied identity equals the observed checkout; it does not prove a completed gate, a clean tree, or absence of live frames or live attempts. The current Codex record includes native launch fields such as agent_type, model, effort, and service_tier, while the live host API may accept a different subset. A probe, rather than prose, must decide which fields are native. If the probe fails, stage 1 fixes only that adapter declaration/emission seam and records the mismatch; broad host expansion belongs to stage 3.

## Bounded changes and causal owners

1. Add example-workflows/implement-spec/SKILL.md as a reusable, manually invoked workflow body. It opens one frame, makes a plan or implementation ticket with existing do, runs independent sibling calls only when the Goal needs them, hands their typed artifact lines to one fresh judge, permits the existing bounded repair idiom, and closes on an outside command. Its Require names goal, standard, judge-standard, workspace, probe, and bound; its Return names the closed run, joined status, artifact identity, and findings path or []. It contains no schema, fixture format, or script in this stage.
2. Add the smallest installer or handoff guard proven necessary by a failing probe. The required invariant is explicit: an install refuses or the handoff procedure blocks while any live frame or live dispatch attempt in the shared user state sink could consume the old substrate. orchflows resume is only a per-project view and is insufficient by itself. Reuse the state-root and existing ticket records; do not add a second run-state store. If the procedure plus a shared-sink operator check is sufficient on the supported host, leave installer code unchanged and record that evidence.
3. Add a host-adapter smoke check for every detected host. A native field is emitted only when the selected host record and probe accept it; a requested capability remains visibly unverified. On this baseline, do not make service_tier a requirement for the current Codex launch unless the live API probe accepts it. Do not add Pi or Antigravity support.
4. Add focused checks for workflow admission, adapter rendering, accepted-source identity, and the live-run handoff boundary. Keep tests at seams; do not re-test existing ticket internals or rewrite the ticket contract.

## Exclusions

Do not add --profile to do/judge here; stage 3 owns that gap. Do not migrate standard schemas, permit workflow scripts/resources, enable mixed-artifact judges, or change autorouting. Do not reimplement do/judge, frames, rings, bundles, pins, workspaces, traces, friction, evolve, or self-improve. The implementation child does not activate an install, push, publish, or retrofit a live run; after the stage commit has passed acceptance, the separate handoff below installs that accepted source so the stage 2 canary can run.

## Practical dogfood exercise

After the stage 1 commit is accepted and installed, make a disposable Orchflows checkout from that accepted source and a disposable scratch project. Run a bounded documentation-only stage 2 canary: one project workflow/reference change using the existing legal workflow shape, with no private script or local narrowing standard yet. Invoke the new workflow by name. Its current command forms are:

    tickets.py frame-open <run> --goal-file <goal> --workflow implement-spec
    tickets.py do <run> --standard orch-code --parent <frame> --goal-file <item-goal> --workspace <scratch> --isolation required --bound <bound>
    tickets.py judge <run> --standard orch-code --parent <frame> --artifacts git:<tip> --goal-file <judge-goal>
    tickets.py frame-close <run> <frame> --done {"form":"command","value":"<probe>"}

The abbreviated lines stand for the existing lifecycle: invoke each emitted launch verbatim, stream the child acceptance/result records, land each candidate with its existing land operation, commit the reserved dispatch-outcome note, and then close the frame. These commands are executable examples against the accepted stage 1 library; the JSON passed to --done is the current canonical command binding. Any future option such as --profile is marked proposed in later specs until its check exists. Read the frame Report before each wave, relay artifact: and findings: lines verbatim, and record command exit codes. The canary must produce a committed documentation change, a fresh judge record, and an outside probe result. Private scripts, private references, and local narrowing standards are stage 2's implementation target and are not prerequisites for this stage 1 canary.

## Acceptance evidence

The implementer records the failing readings for each new seam and then the passing readings: a workflow with no manual-only marker is refused; a workflow adapter renders and syncs; a stale or live-run handoff is refused or blocked; a mismatched accepted source is refused; a supported host's launch carries only its verified native fields; and the scratch exercise completes with a committed artifact: git:<full-commit-id> and an independent findings: line. tools/validate.py, affected tests, tools/regen.py --check when relevant, and git diff --check are the focused checks. The root later runs the full required row once.

The stage's final record includes the source commit, clean-tree reading, full gate result, receipt source commit, install.py doctor --quick result, orchflows sync result, and the scratch run identity. A green installer command without those observations is insufficient evidence.

## Migration, compatibility, and recovery

Existing workflows and existing do/judge invocations remain valid. The new workflow is additive. A host whose native capability is unknown keeps the existing requested-capability behavior and reports it as unverified. Ticket and run state are not rewritten. Before install, save the previous receipt/source commit. To recover, stop new dispatches, preserve active candidates, reinstall the previous accepted commit with install.py --accepted-source <previous-commit>, run orchflows sync, and resume from durable tickets. Never use a source checkout with uncommitted bytes as the accepted identity.
