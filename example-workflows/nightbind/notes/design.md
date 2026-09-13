# Nightbind core design

One lantern keeper survives twelve waves by turning the horde into a deliberately composed retinue. The second-to-second decision is where to stand and which threat to recruit. The run decision is whether to take immediate protection or preserve complementary creatures for two earned transformations. Movement mastery routes crowds past allied area attacks and out of ranged poison/charge telegraphs. Death or the wave-12 boss ends the single run; retry clears it completely.

## Mechanics comparison, before implementation

| Realization | Verb, constraint and choices | Thirty-second episode | Depth and failure experiment |
| --- | --- | --- | --- |
| A. Weaken and throw | Aim a finite-charge projectile at a wounded target; stop damaging it before it dies. Accuracy competes with survival movement. | Kite a Thornback to low health, miss a throw into a weakling, then dodge until recharged. | High execution ceiling but ally auto-fire may kill wanted targets; compare acquisition success with a strict health gate. Could become frustrating rather than tactical. |
| B. Lantern attunement, selected | Recharging lantern binds one real nearby creature through a tactical selection view. Six squad slots and complementary recipes constrain choices. | Need an Emberling to complete a ward recipe, but a Mireling's slow would help now; move toward the Emberling, bind, then kite the incoming chargers. | Spatial exposure, immediate role benefit and future recipe tradeoffs interact. Capture pause accommodates planning without replacing movement. Compare cooldowns and distant versus nearby capture range to expose dominant hoarding or cost-free selection. |
| C. Escort to a ritual | Lure a hostile into a shrine; capturing occupies the shrine until safely delivered. | Herd a ranged creature across the arena while protecting a shrine from chargers, then abandon the delivery to survive. | Rich spatial planning but repetitive hauling displaces the requested horde-survival rhythm; compare idle shrine camping with mobile play. |

B best preserves the requested auto-fighting horde fantasy while making composition legible and agent-playable. Selecting a living nearby target avoids the additional low-health aiming requirement, and recruiting fits into the combat rhythm. Captured companions can still kill a wanted recruit before the keeper intercepts it; core play confirmed that timing remains a choice, especially with long-range allies. Capture mode is a public tactical pause that lists only live enemies within lantern range. It spends one charge and removes exactly that enemy through the normal rules.

## Established loop and progression

- Click ground to travel; WASD/arrows steer directly. Player bolts provide a modest baseline; companions attack automatically.
- Lantern holds one charge, regenerating every 11 seconds. It starts full. Binding takes a free slot; six slots, dismissible with an explicit button. Leaving it full wastes recharge time.
- Six roles: Emberling splash damage, Thornback shielding/knockback, Voltwing chains, Mireling slowing poison, Fangling single-target pounce, Mourning Moth healing.
- At wave 5 complementary pairs can become Pyre Warden, Storm Serpent or Dusk Reaper. At wave 10 each first evolution plus two specified base roles can ascend. Recipes are visible from the title and in the field guide. Evolution consumes ingredients and frees squad space. This is an earned gate, never a free replacement weapon.
- Waves 1–3 teach movement and distinct roles; wave 4 compresses space; wave 5 provides the first release. Waves 6–8 combine spitters, charges and crowds; wave 9 presses the build; wave 10 unlocks the ascension. Wave 11 tests its coverage; wave 12 summons the Bellkeeper with telegraphed rings and aimed volleys.
- Two viable approaches: Pyre Warden clears dense packs and protects the keeper; Storm Serpent controls spread ranged threats. Dusk Reaper trades broad clearing for focus damage and recovery. Their ascensions exaggerate these strengths.
- Return play experiments with a different recipe and movement route. No permanent grind or saved progression in this release.

## Initial tuning hypotheses

| Parameter | Initial | Intended consequence |
| --- | --- | --- |
| Wave duration | 22 s | First release at 88 s, second at 198 s, boss at 242 s |
| Charge interval | 11 s | About eight opportunities before first gate, mistakes recoverable |
| Capture radius | 13 units | Choose a route to the wanted creature, without pixel targeting |
| Team capacity | 6 | Keep ingredients versus immediate role diversity; recipes free space |
| Keeper speed / arena radius | 7 / 20 units | Escape pursuers, respect telegraphed area denial |
| Busy enemy cap | 240 | Actual crowds, bounded simulation/render workload |
| Target frame budget | 16.7 ms median / 33.3 ms p95 hypothesis | Measure real production preview later; do not claim hardware coverage from this target |
| Asset budget | ~100k visible triangles, <120 calls, <12 MB initial | Instanced repeated creature parts; final Blender budgets to be specified after core |

## Experiments planned before implementation

1. **Recruitment cadence:** same wave-4 missing-recipe fixture, 18 s versus 11 s charge. Predict 18 s makes a wrong capture consume too much of the pre-evolution recovery window. Observe whether the player can recover a mistaken role while dodging. Keep scarce enough to plan, permissive enough to recover.
2. **Evolution relief:** same wave-5 dense mixed pack with two valid ingredients, evolution multiplier low (1.35) versus intended strong (3.2 equivalent damage plus area/role change). Predict weak evolution leaves the same kiting decisions and no release; intended version visibly removes nearby crowd pressure while ranged/charge threats still require movement. Compare observed crowd, health, ability events and actual rendered motion.

Other acceptance scenarios: ordinary complete run and retry; deliberately poor captures; all three recipes and ascensions; hoarding/full roster/dismiss; edge and diagonal motion; pause/focus/resume; boss victory and defeat. Legal scenario fixtures are diagnostic entry only. Ordinary play is recorded separately.

## Observed core decisions

The recorded comparisons and ordinary run are in `core-playtest.md`. Retained 11-second capture charge after an observed missing-role recovery opportunity. Retained full evolution damage while acknowledging that the weak variant also gave local relief through area coverage. Increased wave-9 spawn pressure from 10 to 18 per second after the ordinary six-companion build arrived too comfortably at the second gate; a same-route no-ascension control separated the evolved companion's clearing from wave 10's own lower spawn rate. Tightened the camera and increased creature size after normal screenshots showed distant, indistinct creatures. Final Blender silhouettes and human feel remain review tasks.
