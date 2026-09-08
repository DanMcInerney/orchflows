---
name: tiktok-video
description: Migrate legacy Orchflows marketing video briefs to orchflows-videos; report scope limits for other video requests.
disable-model-invocation: true
---

Require: the original legacy brief, constraints and available evidence, including
partial inputs and identities.

    tickets.py frame-open <run> --goal-file <legacy-goal> --workflow tiktok-video
      --context-file <legacy-context>

For an Orchflows marketing brief, invoke `orchflows-videos` with every supplied
semantic input, constraint, identity and gap. Opening that public owner establishes
its scope before any private helper or standard resolves.

    tickets.py frame-open <run> --parent <frame> --goal-file <legacy-goal> --workflow orchflows-videos
      --context-file <legacy-context>

Drive the new body in that frame. For an incompatible generic brief, return an
explicit scope/migration result preserving the brief and partial evidence: the
new owner serves Orchflows marketing; independently reusable short-videos can
still guide a separately scoped code assignment. Do not manufacture brand intent.

Never: resolve the new owner's private names in this compatibility scope, duplicate
its rendering flow, discard partial inputs, or rewrite historical pinned artifacts.

Return: `tickets.py frame-close <run> <frame>`; forwarded result identities and
findings verbatim when invoked, otherwise the scope/migration explanation with
original inputs, partial evidence and gaps (`[]` when none).
