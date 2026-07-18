---
name: orch-triage
description: Triage a queue of items into agent-ready dispositions with compacted briefs. A scheduled snapshot, never a loop.
role: none
---

Require: the queue (ticket directories, inboxes, or listed items) and
the disposition vocabulary: ready-for-agent, needs-info,
ready-for-human, wontfix.

For each item, decide from the item's own content plus cheap checks —
never deep investigation, which is the dispatched work's job. An item
disposed ready-for-agent gets a compacted brief: objective, the evidence
already known, and the recommended entrypoint skill. needs-info names
exactly what is missing; ready-for-human names why an agent should not
decide it. Reread an item immediately before writing it; another session
may have moved it.

Never: fix items while triaging; dispose an item on a stale read; let
the snapshot become an open-ended loop.

Return: per-item dispositions, the briefs, and queue statistics.
