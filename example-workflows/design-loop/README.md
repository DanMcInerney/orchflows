# Design loop

> **Experimental — this packaged example is untested so far.** Its end-to-end behavior has not been validated in this standalone form. The trial files below describe intended checks, not completed tests.

Give this workflow a project endgoal and a cycle count. It is designed to start with a small working proof of concept, then use evidence from each attempt to choose the next increment:

**Endgoal → brainstorm + research → design → implement → test → analyze → repeat.**

The coordinator calls small, reusable workflows. Each component can also run independently with the inputs described in its skill and the [shared handoff contract](references/design-loop-contract.md).

## Detailed flow

```mermaid
flowchart TD
    U(["User: endgoal, workspace, criteria, constraints and N"])
    U --> INIT["design-loop: resolve context and bounds<br/>Preserve initial accepted baseline or verify checkpoint"]
    INIT --> START["Start or resume cycle<br/>New attempt consumes one of N; checkpoint each returned stage"]
    START --> B

    subgraph BR["brainstorm-research — composes two reusable workflows"]
        B["brainstorm-options · orch-work<br/>Propose 2–4 increments from goal, baseline and observations"]
        B --> R["research-options · orch-work<br/>Investigate decision-relevant uncertainties<br/>Return sources, findings, tradeoffs and gaps"]
    end

    R --> D["design-increment · orch-work<br/>Choose one bounded increment<br/>Define acceptance and old-versus-new evaluation before edits"]
    D --> CHANGE{"Justified change?"}
    CHANGE -->|Yes| C["Coordinator: isolate candidate from accepted baseline<br/>First cycle: smallest useful working PoC"]
    C --> I["implement-increment · orch-work<br/>Implement the design and perform ordinary checks<br/>Return reproducible candidate; freeze its state"]
    I --> T["test-increment · orch-review<br/>Fresh independent tester compares exact old and new states<br/>Same relevant harness and conditions; no repairs"]
    CHANGE -->|No| SKIP["Mark implementation and testing inapplicable"]
    T --> A["analyze-iteration · orch-work<br/>Assess acceptance, regressions and evidence gaps<br/>Recommend adopt or retain; record lessons"]
    SKIP --> A
    A --> DEC{"Coordinator checks recommendation<br/>against criteria and evidence"}
    DEC -->|Adopt| AD["Accepted state becomes candidate"]
    DEC -->|Retain| KEEP["Accepted state stays baseline"]
    AD --> SAVE["Checkpoint decision, exact accepted state,<br/>evidence, counts and next-cycle observations"]
    KEEP --> SAVE
    SAVE --> CONT{"Attempts remain and no early-stop condition?"}
    CONT -->|Yes: use accepted state and observations| START
    CONT -->|No| OUT(["Return accepted project and usage instructions,<br/>initial-to-final evidence, decisions, gaps and checkpoint"])

    FAIL["Any stage fails: preserve evidence<br/>Mark dependent stages unexecuted"]
    FAIL --> AVAIL{"Scheduled analysis child available?"}
    AVAIL -->|Yes: partial evidence| A
    AVAIL -->|No| MISSING["Record missing analysis and retain baseline"]
    MISSING --> SAVE

    classDef work fill:#ecfdf5,stroke:#059669,color:#064e3b;
    classDef review fill:#f5f3ff,stroke:#8b5cf6,color:#4c1d95;
    classDef coordinate fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a;
    class B,R,D,I,A work;
    class T review;
    class INIT,START,C,CHANGE,SKIP,DEC,AD,KEEP,SAVE,CONT,FAIL,AVAIL,MISSING coordinate;
```

The failure branch applies to any failed stage; failures and skipped work remain visible in the checkpoint. Corrections belong to a later bounded cycle. A paused cycle resumes its first unfinished stage after validating recorded state identities and remaining bounds.

## Reusable workflows

| Workflow | Responsibility | Fresh children per call |
| --- | --- | --- |
| [design-loop](skills/design-loop/SKILL.md) | Coordinate bounded cycles, checkpoints and adoption decisions. | At most 6N through components |
| [brainstorm-research](skills/brainstorm-research/SKILL.md) | Compose brainstorming and research in sequence. | 2 through its leaves |
| [brainstorm-options](skills/brainstorm-options/SKILL.md) | Propose scoped increments and uncertainties. | 1 via `orch-work` |
| [research-options](skills/research-options/SKILL.md) | Investigate uncertainties and return decision evidence. | 1 via `orch-work` |
| [design-increment](skills/design-increment/SKILL.md) | Define scope, acceptance criteria and comparison plan. | 1 via `orch-work` |
| [implement-increment](skills/implement-increment/SKILL.md) | Build an isolated, reproducible candidate. | 1 via `orch-work` |
| [test-increment](skills/test-increment/SKILL.md) | Independently compare baseline and candidate without repairs. | 1 via `orch-review` |
| [analyze-iteration](skills/analyze-iteration/SKILL.md) | Recommend adopt/retain and inform the next brainstorm. | 1 via `orch-work` |

A full cycle uses six fresh children. Composers run in the caller and add none; there is no extra final review or hidden repair loop. `N` counts attempted cycles, including the first PoC and failed attempts, and defaults to 3. A run uses at most 6N child calls, including interrupted calls and replacements.

The loop runs through N unless the caller stops, a stated resource bound is reached, required capability or authorization is missing, or the caller explicitly chose stop-on-goal. Goal attainment alone does not shorten the run. Adoption requires evidence that the increment meets its acceptance criteria and preserves required existing behavior. Otherwise the accepted baseline remains in place, and the next brainstorm receives the observations.

## Install and use

From an Orchflows checkout:

```sh
python scripts/orchflows.py setup --example design-loop
```

Then register or refresh the `design-loop` library through your host using the core's host installation instructions. Setup copies the example into the Orchflows home and preserves an existing library; it does not install project tools. Start a new host session if required for native skill discovery.

Example request:

> Use design-loop:design-loop to build a local shopping-list CLI in this workspace. It should add, list and remove items and persist them between commands. Use Python's standard library. Run N=2 cycles, starting with the smallest working PoC, and leave usage instructions and comparison evidence in this workspace.

Supply the project endgoal, starting workspace or artifacts, and an output directory. Optional inputs include N, success criteria, constraints, selected domains and scoped model/effort choices. Unspecified model settings stay with the host. An empty workspace is a valid initial baseline; existing uncommitted and relevant untracked work must be preserved.

## Dependencies and evaluation status

- Orchflows core `orchflows` 0.7.0+ with `orch-work`, `orch-review` and a host supporting native child delegation.
- Task-specific tools for research, implementation, inspection and testing, plus reproducible state snapshots. The example bundles no project runtime or research service.
- This library's [design-iteration guidance](guidance/design-iteration.md), combined with caller-selected task domains as described in [library context](references/library-context.md).

The [portable trial request](trials/request.md) and [expected behavior](trials/expected-behavior.md) are specifications for future validation. Packaging and Markdown checks do not establish workflow behavior. Keep actual execution reports and project artifacts outside the installed library.
