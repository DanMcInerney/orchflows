---
name: make-short-video
description: Make an original short video through an editable project and rendered exports using one maker.
---

Reuse or establish [library context](../../references/library-context.md). Resolve the film's subject, audience, genre, intent, placements and caller constraints from the request. Carry supplied assets, sources and profile facts. Load [Remotion guidance](../../references/remotion.md) only when Remotion is chosen.

For requested inspiration or research, pass the optional [short-form observations](../../references/short-form-reference.md). They add source context, not another stage or agent.

Invoke `orchflows-light:orch-work` once with the complete brief, output workspace and resolved guidance paths. Keep this delegation entrypoint in the caller; give the child the production assignment:

> Create the film from original concept through an editable project and actual rendered exports. Use the available authoring tools, check your result and deliver the requested placements. Return export paths and SHA-256 identities, editable source and assets, how to reopen and render, and any unresolved constraints or capability gaps. Work without child agents.

When the caller gathers, return the native worker handle and expected output location immediately. Otherwise await the worker and return its actual result. This leaf launches no reviewer.
