# Orchflows: design and operating model

Orchflows is a library of Markdown procedures for agents with native subagents. It separates **the work requested**, **the process to follow**, and **the standard of quality**. Users reuse small workflows inside larger ones and change model-specific guidance without rebuilding the process.

This is the human design report. [Agent contracts](docs/architecture.md) own execution rules; [host documentation](docs/hosts.md) owns platform details. Development history stays in the local, ignored `design/` directory.

## What are the building blocks?

```mermaid
flowchart LR
    P["Prompt<br/>Task · constraints · budget"] --> C[Coordinator]
    W["Workflow<br/>Dependencies · gates · bounds"] --> C
    G["Guidance<br/>Quality · methods · taste"] --> C
    C --> M[Native maker]
    C --> R[Native reviewer]
    M --> O[Result + evidence]
    O --> R
    classDef coordinate fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:2px;
    classDef work fill:#ecfdf5,stroke:#059669,color:#064e3b;
    classDef review fill:#f5f3ff,stroke:#7c3aed,color:#4c1d95;
    classDef guidance fill:#fefce8,stroke:#a16207,color:#713f12;
    class P,W,C coordinate;
    class M,O work;
    class R review;
    class G guidance;
```

| Component | Responsibility |
| --- | --- |
| Prompt | Current result, sources, constraints, permissions, limits and requested settings. |
| Workflow | Reusable inputs, dependencies, allowed effects, outputs, review gates and stopping conditions. |
| Guidance | Quality criteria, role-specific methods, taste and removable model corrections. |
| Coordinator | Resolve scope, apply workflows, staff assignments, join results and preserve bounds. |
| Native host | Skill discovery, agent execution, tools, permissions and available isolation. |
| CLI | Install/update packages, resolve paths and inspect transcripts. It does not execute workflows. |

## Which skills are built in?

There are **five built-ins: two primitives and three workflows**.

| Built-in | Contract | Model-selected automatically? |
| --- | --- | --- |
| [`orch-work`](skills/orch-work/SKILL.md) | Launch a fresh maker with an assignment and applicable guidance. | No |
| [`orch-review`](skills/orch-review/SKILL.md) | Launch a fresh reviewer who made none of the candidate; review without repairing. | No |
| [`orch-review-revise-once`](skills/orch-review-revise-once/SKILL.md) | One independent review, at most one coordinated repair pass, then checks. | No |
| [`orch-build-workflow`](skills/orch-build-workflow/SKILL.md) | Author, rehearse with fixtures, independently review, repair and deliver a reusable workflow or guidance. | No |
| [`orch-dynamic-workflow`](skills/orch-dynamic-workflow/SKILL.md) | Form and execute an ad hoc plan for a top-level task. | Eligible |

All five support explicit selection. Other shipped library skills request manual invocation. Codex uses native `allow_implicit_invocation` metadata; Claude-compatible hosts use `disable-model-invocation`. ZCode cannot enforce manual-only selection; Antigravity's enforcement is unverified.

Manual invocation and composition are different operations. A coordinator can apply declared dependencies by reading their files; it need not invoke a native skill tool at every step. A host rejection is not permission to bypass its controls.

## How is a task routed?

```mermaid
flowchart TB
    U([Task]) --> N{Explicitly selected<br/>workflow or primitive?}
    N -->|Yes| S[Apply that process]
    N -->|No| H{Host selects dynamic?}
    H -->|Yes| D[Plan and execute<br/>an ad hoc workflow]
    H -->|No| O[Ordinary host behavior]
    S --> C[One coordinator]
    D --> C
    classDef decision fill:#fefce8,stroke:#a16207,color:#713f12;
    classDef selected fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:2px;
    classDef neutral fill:#f8fafc,stroke:#64748b,color:#0f172a;
    class N,H decision;
    class S,D,C selected;
    class U,O neutral;
```

This describes host/model selection, not a routing engine. Named workflows keep their process; a missing named workflow remains a gap rather than silently becoming dynamic. Dynamic does not wrap selected primitives or restart inside children.

Automatic selection is best-effort. Recorded Claude trials selected dynamic for research-to-code but skipped it for a trivial file-writing request. Explicit invocation worked. Select it explicitly when the process matters.

## What does dynamic decide?

It establishes the result and checks, stages, dependencies, guidance, review gates and bounds. It can reuse saved workflows or assemble assignments directly. A plan does not become a saved skill unless requested.

The default is one independent review of the joined final result. Intermediate gates belong where later work depends on research or design decisions costly to reverse. Independent assignments can run concurrently; shared decisions settle before dependent work.

A research-to-code task can use parallel research → joined research review/fix → parallel coding → joined code review/fix. A clear task can use direct coordinator work followed by review. Staffing is flexible; an explicit `orch-work` call always requires a fresh maker.

## How can workflows nest without nested orchestrators?

Procedure depth and agent depth are separate. The same coordinator applies a workflow, its sub-workflows and their dependencies. Only actual work/review assignments launch agents.

```mermaid
flowchart TB
    subgraph P[One coordinator applies the procedures]
        A[Project workflow] --> B[Research workflow] --> C[Comparison workflow]
    end
    P --> W1[Research worker]
    P --> W2[Another worker]
    P --> R[Independent reviewer]
    W1 & W2 & R -. Results and gaps .-> P
    classDef procedure fill:#eff6ff,stroke:#2563eb,color:#1e3a8a;
    classDef maker fill:#ecfdf5,stroke:#059669,color:#064e3b;
    classDef reviewer fill:#f5f3ff,stroke:#7c3aed,color:#4c1d95;
    class A,B,C procedure;
    class W1,W2 maker;
    class R reviewer;
```

Children cannot launch, assign or continue agents, including through alternate tools. They return outcomes and requests for further work. Loading another procedure neither adds a review nor resets an attempt limit. Local guidance, settings and output paths remain scoped to that call, not its siblings.

## What does a worker need if it remembers nothing?

`orch-work` and `orch-review` address the **coordinator**, not the child. The coordinator gives each child:

- Intended result and acceptance criteria.
- Relevant inputs, sources, candidate identity and prior evidence.
- Applicable guidance paths and role: common criteria plus Make or Review.
- Workspace, output location and ownership.
- Caller constraints, permitted effects, bounds and required checks.

The child can reconstruct the problem without the parent's conversation. A reviewer gets the stable candidate and criteria without the maker's argument. Missing required isolation is disclosed. Children may read domain references; loading delegation skills is not their job.

## How does guidance compose?

Callers can supply an ordered list of files. Named domains provide a convenience: visit dotted prefixes from general to specific, reading core then selected libraries in caller order at each prefix.

For `code.api` with one personal library:

```mermaid
flowchart LR
    A[Core: code] --> B[Personal: code]
    B --> C[Core: code.api]
    C --> D[Personal: code.api]
    classDef core fill:#eff6ff,stroke:#2563eb,color:#1e3a8a;
    classDef personal fill:#fefce8,stroke:#a16207,color:#713f12;
    class A,C core;
    class B,D personal;
```

Keep each file once. More-specific preferences win within a domain; independent domains combine. Missing implicit parents are allowed, but explicitly selected domains/files must exist. Unresolved requirement conflicts block dependent work.

Common criteria apply to makers and reviewers; optional Make and Review sections supply role-specific instructions. Local extensions refine taste, not permissions, review obligations or caller limits. Reading another scope's guidance as evidence does not adopt its preferences.

## What does review establish?

It supplies an independent judgment of an identified state and scope. The candidate stays stable until required judgments finish. Reviewers can run isolated checks but do not repair it.

`orch-review-revise-once` permits one coordinated repair pass after review, followed by affected and caller-required checks—even when no repair is needed. Missing or incomplete review blocks repair. The original verdict stays attached to the inspected state; a revision does not inherit it. There is no automatic second review or release authorization.

Other workflows own their review counts. Dynamic preserves component gates and counts an existing review only when candidate, criteria and scope match its planned gate.

## How does workflow building avoid touching real data?

```mermaid
flowchart LR
    E[User examples<br/>read-only] --> F[Generate realistic<br/>synthetic fixtures]
    W[Candidate workflow] --> T[Disposable rehearsal]
    F --> T
    T --> S[Local service fakes<br/>captured email/API payloads]
    S --> J[Complete checks<br/>and required judgments]
    J --> R[Independent<br/>authoring review]
    R --> D[Deliver workflow<br/>evidence + gaps]
    classDef reference fill:#eff6ff,stroke:#2563eb,color:#1e3a8a;
    classDef local fill:#ecfdf5,stroke:#059669,color:#064e3b;
    classDef simulated fill:#fefce8,stroke:#a16207,color:#713f12;
    classDef review fill:#f5f3ff,stroke:#7c3aed,color:#4c1d95;
    class E,W reference;
    class F,T,D local;
    class S simulated;
    class J,R review;
```

Trials use the smallest representative local rehearsal. Supplied documents are not transformation targets. External reads use fixture responses where possible; writes use capture fakes. Email/calendar tests produce drafts and fake receipts, not real deliveries. A directory alone does not isolate a remote API.

Real content is copied only when essential and authorized for the trial; originals stay read-only. A sandbox or dry-run must be verified to avoid live resources. Live trials require an explicit request covering their effects. If no safe test exists, record an untested branch instead of performing it. Normal authorized execution remains separate from authoring tests.

Simulated services do not replace real independent reviewers. Finish selected trials and their judgments before authoring review. Report simulations and unverified integrations; static checks do not prove workflow behavior.

## How are limits and model settings preserved?

A bounded attempt counts before its first work, including failures and pauses. Resumable loops persist attempt identity, starting state and count; resumption continues that attempt. Composition and replanning do not replenish budgets. Each workflow defines its iteration and stopping rule; there is no universal checkpoint format.

Model and effort resolve separately. Current caller choices override saved preferences; within either source, assignment overrides stage, then operation default. Unspecified fields use native defaults. Authoring-session settings are not silently saved into new workflows.

Apply settings through actual host controls, including repairs. Direct work or reuse is valid only when it honors those settings; otherwise use a fresh worker. Unsupported controls are reported, not approximated with a model name in the prompt.

## What else ships?

Eleven optional [example libraries](https://github.com/DanMcInerney/orchflows/tree/main/example-workflows) provide 26 additional, manual-only entrypoints: social search, research acquisition, short video, browser games, candidate comparison, software delivery, design loops, benchmark building, evolution, self-improvement and standalone export. They consume core; they are not extra primitives. Each declares dependencies and validation status. Setup does not install transitive library dependencies.

| Location | Owner and purpose |
| --- | --- |
| Source checkout | Library developers; edit core here. |
| `~/.orchflows/libraries/<name>/` | User-owned workflows/guidance; new workflows default to `personal`. |
| `~/.orchflows/.local/packages/orchflows/` | Setup-managed core; replaced on update. |
| Task workspace | Results, checkpoints and evidence, outside packages. |

The dependency-free Python CLI provides `setup`, read-only `doctor`, `resolve`, and native `history` access for Codex/Claude. Registration is not proof of authenticated execution. [Home and CLI contracts](docs/home.md).

## What is deliberately not guaranteed?

Orchflows has no execution engine, scheduler, workflow DSL or host-enforced process checker. Its contracts depend on agents following instructions and hosts exposing required capabilities. Missing capability is reported rather than silently replaced; self-review cannot replace independent review.

Recorded trials include successful flat composition and staged review/repair, but also missed automatic selection, dropped output limits and timeouts. A completed six-child research-to-code run passed code checks yet failed a report-length constraint. These remain failures in the [test record](https://github.com/DanMcInerney/orchflows/tree/main/tests/e2e), not evidence of universal reliability.

The design aims to preserve useful processes as models improve: retain dependencies and judgments, remove obsolete corrections from guidance, and validate changes on representative work. More agents are useful when their independence or parallel work earns the coordination cost.
