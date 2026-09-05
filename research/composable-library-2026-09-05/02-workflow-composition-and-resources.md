# 2. Workflow composition and resources

Status: proposed. Implement only after stage 1's accepted source and handoff evidence are present.

## Dependencies

Stage 1's installed commit and its implement-spec workflow; the existing ring resolver, bundle pins, custom authoring owner, rules/composition.md, and contracts/bundle.md. The accepted predecessor is the source and runtime substrate. The implementation uses the code standard and may add no new package manager.

## Goal

A workflow author can publish one reusable workflow whose public body composes smaller workflows, deterministic scripts, and private resources, while keeping local narrowing standards and helpers private unless exported. Existing workflows continue to resolve and run unchanged, dependency environments remain per item, and composition remains acyclic and bounded by real dispatch/workspace limits.

## Current-code evidence

rules/composition.md already defines callable anatomy, exact backtick call edges, acyclic graphs, Return carriers, failure evidence, and placement. docs/custom-workflow-authoring.md already defines project/home/import/lib rings, bundle pins, trust, per-item Python/Node/tool dependencies, and workflow adapter rendering. Its current workflow admission explicitly refuses scripts and workflow-local schemas/fixtures, and its Require rule forces every item through a named T0 carrier even when no machine consumer exists. scripts/orchflows_adapters.py renders an inert pointer and disable-model-invocation: true; scripts/rings.py and standards_support.py resolve global items. The requested feature therefore needs a narrowly owned package boundary, not a second resolver or a new DSL.

## Bounded changes and causal owners

1. Extend the custom workflow package contract in docs/custom-workflow-authoring.md and the workflow validator to allow an item's own scripts/ and owner-named private references/ files. Reuse references/ for prose, fixtures, schemas, and other resources; a subdirectory is private unless the public body exports its path. A workflow-local schema or fixture is allowed when a private script is its actual consumer and no library resolver branches on it. The workflow still has exactly one public SKILL.md. The workflow validator owns shape and containment; the authoring document owns scope and trust.
2. Add deterministic script execution through the existing environment classes. A workflow's requirements.txt, tools.txt, and optional package.json/lockfile remain beside the workflow manifest, are synced per item, and are never installed into the library tree. A script returns stdout, exit code, and partial evidence through the existing result channel. It cannot mutate another item or the run sink directly.
3. Permit a private narrowing standard to be referenced by an explicit proposed --standard-file <path> input at a workflow call site. The path is resolved relative to the workflow package, pinned with its digest and parent chain at ticket issue, and is not added to the global standards inventory. The normal --standard NAME form and ring resolution remain the public default. This flag is justified by the concrete need for local QA/house style without global advertisement; it is not a namespace syntax.
4. Permit a private smaller workflow/helper to be referenced by an explicit proposed --workflow-file <path> input. The path is contained by the owning workflow, is absent from global list and host adapters, and is resolved through the same callable contract. Public workflow calls keep the resolver's exact backtick grammar because the resolver consumes those edges. A private helper path, a local Require sentence, and a local idiom may use concise free-form prose when no machine consumer needs a T0 carrier or canonical wording; the workflow contract and Return envelope still bind. The validator must reject an actual unresolved callable edge, cycle, escape, or missing Return.
5. Keep calls explicit in workflow prose. A workflow may call another workflow once at each prose call site; the resolver rejects a cycle and reports the exact path. Bound depth by the existing maximum dispatch/workflow depth and call budget rather than inventing a daemon. A grouped step may stay in one child when it owns one coherent artifact and one workspace; fan-out earns separate children when isolation or independence is needed.
6. Add seam checks for private path containment, trust refusal, dependency environment selection, cycle/depth refusal, digest pinning, script exit/evidence forwarding, a workflow-local consumer schema, and compatibility of a legacy workflow with no new directories.

## Exclusions

Do not expose private helpers through global list, host adapters, or by-name pointers. Do not add a universal workflow schema or fixture taxonomy; local formats may exist only with a private executable consumer. Do not permit import-time code execution, a package manager, daemon, scheduler, or mandatory one-agent-per-step policy. Do not make a private standard silently autorouted. Do not let a workflow change a live run's installed source or bypass tickets/workspaces for risky writes.

## Practical dogfood exercise

Create a project workflow browser-game-qa with a public body, a private browser-check script, a private references/ file containing the check's instructions, and one local narrowing standard that tightens the code standard. Create a private helper workflow beside it and compose both from a second public workflow. Run the canary through implement-spec in a disposable browser-game repository. The workflow should call a public research or build workflow, run its private check, hand the resulting git:<tip> to an independent judge, and report a missing browser as a typed partial result. orchflows list must show only the public workflows; orchflows check must grade the private files through their owning validators. Repeat with a second public workflow that composes browser-game-qa to prove reuse without a global alias.

## Acceptance evidence

Record failing and passing readings for: a script under a workflow being rejected before this stage and accepted after; a workflow-local schema with no private consumer being refused while one with its owning consumer is accepted; a private reference escaping its package being refused; a private standard and helper omitted from list but pinned and read by their named calls; a cycle and over-bound chain refusing; an untrusted project item refusing with the existing trust remedy; a missing tool returning partial evidence; and a legacy workflow rendering the same inert adapter. Verify the bundle pin and per-item environment identity, affected validator/routing tests, tools/regen.py --check, and the stage probe. An independent judge reviews the joined workflow and source tree, including the private/public boundary.

## Migration, compatibility, and recovery

Existing public workflows retain their current directory shape and adapter output. Existing references/ links remain public only when the owner names them; unnamed references/ subdirectories default private. No ticket field is removed. A workflow that used a refused script must move it into its own package and declare its tooling; it is not silently interpreted under old rules. If an accepted package causes a bad run, retire the attempt, preserve the candidate and reports, restore the previous accepted library, and resume the workflow from its frame rather than deleting private state. A private standard's digest change invalidates only tickets that pinned it; existing accepted runs remain on their pinned source.
