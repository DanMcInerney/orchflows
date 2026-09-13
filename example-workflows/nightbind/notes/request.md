# Nightbind: requested game and working scope

This is a full dogfood run of the repository's `example-workflows/3d-browser-game` workflow, not the earlier bounded salvage trial. Run all production stages, including original Blender assets and independent final playtesting.

## User requirements

Build a Vampire Survivors-like horde survival game. Instead of collecting weapons, the player gradually acquires a capture item, similar in function to a Poké Ball, and can capture one enemy to fight on their side every X seconds. Certain combinations of captured enemies evolve into a much stronger monster.

The pressure should rise until the player nearly feels overwhelmed, then good capture choices yield a dramatic evolution power spike. Do this twice in one run, with around 12 waves, evolution spikes around waves 5 and 10 and a boss at the end. Enemies must be numerous, varied and interesting enough that capture choices matter. One run, not 12 separate matches.

## Chosen production defaults

- Working title: Nightbind. Original dark fantasy creatures and capture device, with a cohesive stylized 3D look.
- Desktop browser, keyboard movement and pointer interaction. Use a public click-to-move/capture route if it benefits ordinary play and agent control; assisted diagnostic controls remain separate.
- One arena and one complete escalating 12-wave run, roughly 4–6 minutes including the final boss, followed by an outcome and quick replay. The maker may tune wave lengths to serve pacing.
- Companions fight automatically. Survival movement and selecting captures/combinations are the player's principal decisions.
- The maker chooses capture cooldown, squad size and concrete recipes through explicit mechanics comparison and experiments. Explain combinations in the game so success depends on planning rather than guessing hidden recipes.
- Require distinct enemy attack/movement roles and distinct allied abilities, multiple viable composition paths, visible anticipation/consequence, and a materially different tier of power at each intended evolution moment.
- Local production preview is the delivery target. No public deployment is requested.

## Observable acceptance

A player can start without external instructions, understand charging/capture and recipes, move through crowds, choose real enemies to capture, keep and evolve companions, experience the wave-5 and wave-10 transitions on a sensible composition, defeat or lose to the final boss, and restart cleanly. Poor choices must differ meaningfully from good combinations without making recovery needlessly opaque. The game must show actual hordes and identifiable enemy roles, not sparse enemies or cosmetic variants.

Independent reviewers must play the core and finished game through ordinary controls. Reproducible diagnostic scenarios must cover pre/post evolution, wrong/missing combinations, each major enemy behavior, boss victory/failure, and restart. Performance measurements must identify the actual browser/backend and busy workload. Preserve gaps honestly.

Outputs belong here, never in the workflow library. The caller owns scope/capability checks, all four child dispatches and joins, and the final handoff. Record friction with the reusable workflow in `notes/dogfood.md` as it occurs.
