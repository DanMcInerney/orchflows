# Rendered UI contract

The observability UI is a local, read-only projection. Its foundation contract
has four coordinated owners:

- `scripts/ui_experience.py` projects the closed, privacy-preserving
  `orchflows.experience.v1` response.
- `web/src/ObserveApp.tsx` owns the persistent shell and the exact
  **Now / Workflows / Create / Sessions / Friction** rail. Create is disabled
  because authoring is future work outside the observer.
- `docs/ui/view-manifest.json` names every deterministic visual identity and
  its wide or compact viewport.
- `tools/ui_frontend.py` captures, audits, and classifies diffs for that
  manifest without admitting captures or goldens to source control.

Feature views register additively through `web/src/app/registry.ts`; they do
not rewrite the shared shell, tokens, router, reader projection, or graph
primitives. Ticket prose is rendered only from the selected closed section
set and remains inert. Transcript content, paths, prompts, tools, commands,
files, and conversations remain outside the browser contract.
