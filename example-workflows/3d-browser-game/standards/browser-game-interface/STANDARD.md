---
name: browser-game-interface
description: Stamp when a browser game's rendered canvas, HUD, menus, focus, and accessibility evidence are judged.
narrows: orch-design
adapter: git
---

The interface is judged from captures at the declared viewport and state
identities. The canvas, menu, HUD, prompts, upgrade choices, damage feedback,
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
truth, focus order, contrast, and console cleanliness. A source-level claim
without the exact rendered capture is unverified visual evidence.
