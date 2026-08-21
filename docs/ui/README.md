# Rendered UI contract

The observability UI is a local, read-only projection. Its foundation contract
has coordinated owners with one-way dependencies:

- `scripts/ui_experience.py` projects the closed, privacy-preserving
  `orchflows.experience.v1` response.
- `web/src/ObserveApp.tsx` delegates to `web/src/app/shell/`, which owns the
  persistent reader chrome and imports the one explicit application feature
  catalog. That catalog owns the exact **Now / Workflows / Create / Sessions /
  Friction** rail. Run and ticket execution descendants activate Now; workflow
  definition detail and source descendants activate Workflows. Create remains
  disabled because authoring is future work outside the observer.
- `web/src/features/` owns each feature's route, schema, request, polling
  policy, projection, model, fixture, style, view, and focused tests.
- `web/src/shared/transport/` owns feature-blind ETag, retry, abort, and timer
  mechanics. Only the catalog-selected mounted feature polls.
- `docs/ui/view-manifest.json` names every deterministic visual identity and
  its wide or compact viewport.
- `tools/ui_frontend.py` captures, audits, and classifies diffs for that
  manifest without admitting captures or goldens to source control.

The audit traverses every manifest identity at its ordinary viewport and also
exercises a 200-percent zoom-equivalent reflow viewport, forced colors,
reduced motion, and complete keyboard reachability parity. A passing default
Axe scan alone is not treated as evidence for those scenarios.

Features are composed once through `web/src/app/shell/featureCatalog.ts`; they
do not self-register or import the catalog, shell, or another feature. Glob
discovery, whole-experience handoff, fallback navigation, and duplicate route
switches are absent. Ticket prose is rendered only from the selected closed
section set and remains inert. Transcript content, paths, prompts, tools,
commands, files, and conversations remain outside the browser contract.

The ownership migration and its contributor recipe are specified in
[`modularization.md`](modularization.md).
