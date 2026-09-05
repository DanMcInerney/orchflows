# 3. Packages and authoring oracle

## Goal

A public workflow package can carry private helpers, standards, references, and scripts. Dispatch and checking resolve every item through the existing rings algorithm with an owning-package scope. The package's existing top-level item remains its public inventory; conventional private folders do not appear in global discovery or host adapters.

Workflow bodies remain prose. Admission catches recognizable broken calls and can exercise a real package probe, while stating clearly what static analysis cannot prove.

## Owners and changes

The ring resolver gains an owning-package scope using the same nearest-first rules, collision handling, trust decision, and pin identity as project, home, imports, and library items. A public workflow name establishes its own scope; private helpers inherit that owner. Conventional private helper, standard, reference, and script folders resolve before outer rings. Existing top-level ring items remain the public inventory; this stage adds no export declaration or package manifest. There is no `--standard-file`, `--workflow-file`, path namespace, or second digest path.

The bundle/package contract and `docs/custom-workflow-authoring.md` define containment and the conventional private folders. Package resources cannot escape; citations to canonical library rules, docs, and contracts may. Trust covers the package and the code it runs. Frames and calls pin the public workflow name, whole-package digest, and contained entry. External bundles remain pinned through the existing dependency closure. Script dependencies use the current per-item environment and tool declarations. Private standards remain ordinary text and use stage 2's standard resolver and pins. Host adapter generation continues to see only existing top-level public items.

The workflow checker reads prose conservatively. It checks complete literal Orchflows commands at recognizable line starts or in code spans, resolving callable names and flags against the CLI and package-aware resolver. Literal obsolete flags such as `--pack` and `--sheet` fail with location and current help. Missing public or private literal names, illegal escapes, and literal private frame-call cycles fail. Dynamic names, branches, and implied natural-language calls are reported once per body as unchecked rather than certified. Static parsing does not claim that arbitrary prose executes.

A package may declare a small fixture and probe using its ordinary resources and scripts. The probe invokes the public workflow or its concrete machine boundary and checks an observable result. Its command is package-owned, optional, and run only after trust; there is no universal fixture schema or required artifact taxonomy. Packages without a probe retain static admission and can be exercised manually.

The authoring guide asks the useful questions: what is public, what stays private, which names must resolve, what code runs, what evidence shows the package works, and what must be pinned? These questions guide prose and review; they are not mandatory headings.

## Exclusions

Do not add a workflow step schema, execution engine, renderer contract, mandatory fixture format, global private-item aliases, or hardcoded game workflow. Do not infer control flow from arbitrary prose or claim static resolution proves runtime success. Do not edit `example-workflows/` in this stage.

## Observable proof

Build a temporary package with one public workflow, one private helper, one local standard, one reference, and one script. Resolve the helper and standard only while the package owns the call, pin them with their ring identity, run the script in the package environment, and verify that global list and generated host adapters expose only the public workflow. Attempted path escape, unresolved literal name, literal cycle, and untrusted execution refuse.

Checker fixtures include a valid literal `do`/`judge` call, an obsolete `--pack` or `--sheet` call, a dynamic prose call that must be labeled unchecked, and a package probe that succeeds only when its actual output exists. A legacy workflow package with no private items resolves unchanged.

A source-backed integration fixture drives the package through the existing `do`, `judge`, frame, and `land` boundaries and an outside probe. It checks public/private containment, dependency pins, the static report, and the probe outcome. A live fresh judge is additional evidence only when available. The slice is ready to integrate when focused rings, trust, package validation, checker, environment, and adapter-generation tests pass.
