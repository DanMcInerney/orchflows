---
name: research-options
description: Investigate bounded uncertainties in proposed project increments and return evidence for choosing a design.
disable-model-invocation: true
---

Use the [handoff contract](../../references/design-loop-contract.md). Inputs: request context, baseline and options with questions; caller-supplied options need no brainstorming stage.

Unless the caller overrides, use at most 3 focused lookup/search operations and 5 relevant sources per invocation. Inspect supplied/local material first, external sources as needed. A lookup reads documentation, project evidence or a public source. Record coverage and uncertainty.

For assignment `research-options`, prioritize questions that could change the choice and gather evidence within bounds. Return source paths/URLs, observations, supported/unsupported claims, tradeoffs, changed preferences and questions. State when local evidence suffices or required external evidence is unavailable. Inaccessible or unchecked sources are not findings.
