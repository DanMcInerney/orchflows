---
name: browser-game-interface
description: Stamp when a browser game's rendered canvas, HUD, menus, focus, and accessibility evidence are judged.
narrows: orch-design
adapter: git
---

Review the rendered interface at every recorded viewport and state key. The
canvas, menu, HUD, prompts, upgrade choices, damage feedback,
telegraphs, terminal state, restart, and re-entry each communicate their job
at gameplay distance. A visual token decision remains consistent across
views, while density and hierarchy keep the next useful action discoverable.

Focus is visible and stable, keyboard reach matches the documented controls,
pointer targets remain usable, and essential information survives color or
motion loss. Text, contrast, hit areas, reduced-motion behavior, and forced
colors are recorded where the brief promises them. Accessibility scope stays
at the authority level of the brief; the standard adds no product promise.

Reviewers require a closed view × breakpoint × state capture inventory,
including loading, empty, error, focus, and terminal states where applicable.
They examine hierarchy, legibility, occlusion, feedback timing, affordance
truth, focus order, contrast, and console cleanliness. Source assertions do
not establish appearance until a matching render has been captured.
