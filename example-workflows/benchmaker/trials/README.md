# Test the benchmark before trusting the score

A runnable benchmark can still reward the wrong thing, or reward nothing hard. These manual scenarios probe whether Benchmaker admits hard, valid tasks, rejects the rest, and reports honestly what the suite measures.

| Scenario | What it probes |
| --- | --- |
| [Known ordering](known-ordering/request.md) | Whether the delivered benchmark separates hidden subject variants of known quality and gives a cheater nothing |
| [Self-benchmark](self-benchmark/request.md) | Benchmaker building a benchmark of benchmark builders, with itself as the target |
| [Planted shortcut](planted-shortcut/request.md) | Whether admission finds an exploitable shortcut the author was not told about |
| [Skill uplift](skill-uplift/request.md) | Paired with/without measurement, activation and non-activation work, leakage and harm |
| [Workflow uplift](workflow-uplift/request.md) | A multi-agent workflow against the same model alone at matched budget |
| [Research](research/request.md) | Hard source-grounded synthesis, citation support and unavailable judging |
| [Coding](coding/request.md) | Real workflow invocation, hidden verifiers, history leakage and valid alternatives |
| [Stateful planning](stateful-planning/request.md) | Reset, preservation, infeasible requests and partial credit |
| [Artifacts](artifacts/request.md) | Actual modality inspection and unavailable judgments |
| [Description only](description-only/request.md) | A useful draft without invented execution |
| [Unreliable adapter](unreliable-adapter/request.md) | Overlap, cleanup, durable partial results and retry/resume |
| [Review and revision](shared-revision/request.md) | Blind audit before disclosure, separate review, one repair and preserved evidence |

```mermaid
flowchart TB
    I[Request + raw inputs] --> B[Build benchmark in a fresh session]
    B --> P[Preserve package, card, rejection log and evidence]
    P --> V[Evaluator runs the delivered benchmark against hidden material where the scenario has it]
    V --> E[Assess against private expectations]
    E --> R[Observed behavior + untested branches]
    classDef make fill:#eff6ff,stroke:#2563eb,color:#1e3a8a;
    classDef evidence fill:#ecfdf5,stroke:#059669,color:#064e3b;
    classDef review fill:#f5f3ff,stroke:#7c3aed,color:#4c1d95;
    class I,B make;
    class P,V evidence;
    class E,R review;
```

Run a request in a fresh workspace, starting it with the host's explicit invocation where it writes `[invoke benchmaker:benchmaker]`. Use the complete library, resolved core and shared packages and guidance, and only the raw inputs. Withhold the authoring conversation, sibling `expected-behavior.md` and any hidden material the trial setup names from the executing author. An independent evaluator uses them afterwards. Save packages, native identities, commands, outputs, timings and findings outside this library. Keep hidden material outside the author's workspace and its parent directory. Claude Code print-mode sessions that delegate need the background-wait setting described under [hosts](https://github.com/DanMcInerney/orchflows/blob/main/docs/hosts.md#delegation).

**Measuring Benchmaker itself.** Known ordering and self-benchmark supply the numbers the other scenarios lack. How often does a delivered benchmark recover the hidden order? How many planted defects does it catch? Does a cheater earn anything? The evaluator obtains these by running the delivered benchmark's own commands against the hidden variants, never by reading the package's claims. Hidden variant pools should draw their defects from documented benchmark and agent failures, not from Benchmaker's own guidance, so the trial does not teach to the test.

These folders have no `case.json` and are not discovered by the automated E2E runner. They specify coverage to exercise; they do not establish execution or cross-domain acceptance. Known ordering ran once, on September 23, 2026, before the difficulty and known-order fixes; [DESIGN](../DESIGN.md) records its lessons. **No scenario has run against the current process.**
