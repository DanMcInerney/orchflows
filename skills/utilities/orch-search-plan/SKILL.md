---
name: orch-search-plan
description: Produce one canonical bounded candidate-search plan from frozen policy and settled public outcomes.
role: none
---

Require: one UTF-8 JSON request on stdin carrying frozen policy, prior
projection, settled public outcomes, and remaining bound per the
[protocol](references/protocol.md).

Run the sole operation:

    python skills/utilities/orch-search-plan/scripts/search_plan.py advance

Write one canonical JSON response plus LF to stdout. Invalid input exits 2 with
empty stdout and one bounded diagnostic on stderr.

Never: read repository state; write a file; launch a process; use a model,
network, service, plugin, or non-standard-library dependency; infer protected
evidence or campaign judgment.

Return: the `search-advance/v1` response on stdout.
