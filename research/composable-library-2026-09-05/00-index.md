# Composable library implementation series

Status: proposed implementation plan. Baseline: `a7f19004d595fa09ab1aeda685f70002af2388fd`, observed 2026-09-05. These documents describe work to implement; they do not claim the behavior already exists.

The series keeps the current library shape: prose workflows drive the existing `do`, `judge`, `land`, and frame operations; rings resolve named items; tickets pin inputs and preserve results; host adapters translate a resolved assignment into a native launch. The changes remove contradictions and join existing seams before adding package composition.

## Order

| stage | result | primary owners |
| --- | --- | --- |
| 1. [Defects and usable bootstrap](01-defects-and-usable-bootstrap.md) | Installation works without a ceremonial flag, explicit source assertions stay strict, and standards have one public pin identity | `install.py`, `installer/packages.py`, `standards_support`, `tickets_pins`, ticket help |
| 2. [Standards and workspaces](02-standards-and-workspaces.md) | Domain guidance composes independently of one execution-owned workspace selection | standard contract and authoring docs, `standards_support`, `tickets_adapters`, ticket mint/admission |
| 3. [Packages and authoring oracle](03-packages-and-authoring-oracle.md) | A workflow package can keep helpers private and can be checked and exercised without a second resolver or a workflow language | rings, bundle/package validation, custom authoring docs, checker |
| 4. [Profiles, inline work, and host entry](04-profiles-inline-work-and-host-entry.md) | High-level calls expose existing profile choice, and one assignment may keep context for sequential work | ticket minting, role/kernel contracts, host adapters |
| 5. [Routing, improvement evidence, and proof](05-routing-improvement-and-integrated-proof.md) | Routing says what it will do without inventing team syntax, and improvement evidence is described at its actual strength | host block, ticket routing, improvement docs and existing readers |

Each stage starts from a stable accepted checkout. It runs focused tests while changing the seam and the repository's required checks once before acceptance. Installation happens only when a later phase needs the new runtime and after active consumers of the old runtime have finished. No implementation installs a new global library beneath its own running children.

## Decisions after the Fable review

The review correctly identified the no-flag installer refusal, competing standard digests, duplicated standard parsing/help entries, the `_one_lane` heuristic, and the mismatch between ordinary lane announcements and team shape lines. It also correctly challenged mandatory standard headings, the proposed private-file resolution flags, mandatory workspace-adapter declarations, a new grouped-execution layer, and claims that lexical friction clusters prove semantic recurrence.

This revision does not adopt the proposed install census or a new gate-record authority. `--accepted-source` remains an optional checkout-identity assertion; it is not a test verdict. Workspace selection is derived for normal calls, with an explicit escape hatch and legacy reads where needed. Both directory-backed and run-scoped evidence storage remain valid because they have different lifecycles. Optional `narrows` remains a compatibility convenience for one required base and is flattened with explicit orthogonal standards into the same pin list.

The review's personal aggregate figures about 7,746 friction records, 99.5% singletons, 0.3% qualification, and 29 proposals were not independently verified in this repository. They motivate honest limits, not a new threshold or mechanism. Raw bounded records and agent judgment remain the semantic evidence path.

Workflow notation and changes under `example-workflows/` are outside this series. So are new Pi or Antigravity adapters, a hardcoded game workflow, an `implement-spec` workflow, a workflow step schema, and automatic removal of prompting guidance. Example workflows may be evaluated later against the repaired library, but they do not define this implementation.

## Shared boundaries

Standards are ordinary domain text. Outline, slice, make, review, and vocabulary are useful questions for authors; they are not required headings. Makers and judges read the full applicable compact guidance pinned on their ticket.

Workspace mechanics belong to execution and are normally derived from the concrete target. Standard lists combine orthogonal guidance and resolve to one ordered, deduplicated list of pin identities. A narrowing may name one required base as shorthand; it does not create a second inheritance system.

Workflow packages use the rings resolver with an owning-package scope for private items. Their control flow stays prose. Checkers can resolve recognizable literal names, commands, and flags and can run an optional package probe; they cannot prove arbitrary prose will execute correctly.

Roles remain the existing planner and worker profiles. Operation defaults are preferences, and the host adapter owns actual model and effort transport. One ordinary assignment can perform coherent sequential making and local review in one workspace. Independent acceptance still requires a fresh assignment.

Durability, pin identity, workspace ownership, stale-writer protection, and host facts are lasting guarantees. Routing prompts and authoring questions compensate for current model behavior; keep them concise and mark them as removable when evaluation shows callers no longer need them. Their removal remains an ordinary reviewed code or document change, not a new automatic framework.
