---
name: orch-execute
description: Produce one artifact through the stamped pack's craft and return its durable ticket envelope.
role: worker
---

Require: one claimed ticket with a stamped pack digest and its semantic
assignment.

Resolve the stamped digest through `packs.py cells <digest>` and read the
whole craft document. Work in its `## Workspace` semantics through its
`## Stages`; choose implementation, tests, and verification from that craft
and repository law. Stream the executor record as work is produced, then
commit the reserved outcome.

Never: substitute a skill name for a pack cell; invent a domain rule outside
the resolved pack or shared rules; edit sealed semantics; integrate another
candidate; or claim an artifact without the pack's evidence.

Return: the completed ticket with status, result identity, verification, and
the pack evidence record.
