# Request

[invoke `benchmaker:benchmaker`] Build a draft suite measuring how well benchmark-building workflows make benchmarks. The target is the Benchmaker library at `./target-library/`, run as a native workflow in its own top-level session. Compare it against a plain agent given the same request and budget without the library.

Each task hands a builder a subject system, a claim and a budget. It grades the delivered benchmark by running it against a hidden pool of subject variants with a known order and planted defects, plus a do-nothing variant and a cheating variant. A good delivered benchmark recovers the order, catches the defects and gives nothing to the cheater. Subjects must be cheap, non-composing systems that run as single agent processes, such as a command-line tool-using agent on a small model, or the same agent with and without a skill.

Build at least four candidate tasks and admit what survives. Execute each builder once on one admitted task. Verifiers are programs the coordinator runs; the subject runs they launch are ordinary processes, counted separately from builder sessions.

Limits:
- at most 8 builder sessions, ninety minutes each;
- at most 400 subject runs, five minutes each;
- no retries, no paid judge.

Save the suite, commands, card and rejection log in `./benchmark-run/`.

Trial setup: `./target-library/` is a read-only copy of the Benchmaker package, separate from the installed copy running the trial. The session needs permission to launch separate native sessions under core `docs/hosts.md#workflow-trials`. The evaluator keeps a hidden pool of builders and, after delivery, runs one admitted task of the delivered suite against each:

- full Benchmaker;
- a copy of Benchmaker with the admission step removed;
- a plain agent;
- a builder that delivers an empty package;
- a builder that delivers a plausible package whose card and results are fabricated.

Run the pool within its own separately declared budget.
