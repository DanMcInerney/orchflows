---
name: research-options
description: Investigate bounded uncertainties in proposed project increments and return evidence for choosing a design.
---

Use the [shared handoff contract](../../references/design-loop-contract.md). Inputs are request context, baseline and proposed options with questions; caller-supplied options work without brainstorm-options. Uses 1 fresh child.

Unless the caller supplies tighter or broader bounds, use at most 3 focused lookup/search operations and 5 relevant sources per invocation. Inspect supplied/local material first, and use external sources when needed. A lookup can read documentation, project evidence or a public source. Record coverage and unresolved uncertainty.

Invoke core `orch-work` for the named assignment `research-options`, supplying those inputs, source access and resolved Make guidance. Ask it to prioritize the questions that could change the choice, inspect applicable project material and documentation, and gather evidence within the research bounds. Return sources with paths or URLs and relevant observations, supported and unsupported claims, option tradeoffs, any changed preference and unresolved questions. State when local evidence is sufficient or required external evidence could not be obtained. Do not treat inaccessible or unchecked sources as research findings.
