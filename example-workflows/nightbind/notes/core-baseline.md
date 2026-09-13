# Approved core baseline

Core checkpoint: **READY**, `core-220cfa39951c`. The independent report is `notes/core-review.md`; exact source/export hashes are in `evidence/builds/core-220cfa39951c.json`.

**No repair required.** No rebuild or no-op replay was performed after the review. The nine passing rule tests and the review's exact-build ordinary evidence remain applicable. The reviewer played a continuous ordinary Storm → Pyre recovery → Worldcoil run to victory at 265.05 simulated seconds, made eight captures, observed both earned clearing events, lost with a no-capture approach, and verified both retries. Scenario checks covered three first evolutions, full-roster replacement, pause and public/diagnostic input parity.

The art handoff may change presentation. Preserve this mechanical contract unless the game maker records and retests an intentional later change:

| Contract | Approved value / owner |
| --- | --- |
| Coordinates | World X right, Y up, Z ground depth; floor Y=0; current creature forward is +Z |
| Player traversal | Speed 7 units/s, normalized input, center constrained to circle radius 19; click target coordinate clamp ±19 |
| Ground/layout | Circular floor radius 20.2; no mesh-derived collision, pillars/decoration outside traversal; no interior blocking props |
| Ordinary camera at 1280×720 | Orthographic position (0,36,28), look at (0,0,0), half-height 18, half-width 32; 20 pixels per horizontal world unit |
| Narrow camera | Aspect below 1.3 uses half-height 22; preserve before any intentional camera retuning |
| Timing | Fixed 1/60 s simulation; wave duration 22 s; waves 5/10 at 88/198 s; boss at 242 s; live catch-up bounded to eight steps |
| Capture | One charge, 11 s recharge, radius 13, living base enemy, six squad places, normal tactical pause |
| Contact rules | Non-boss enemy center distance <0.72 damages; boss <2; incoming projectile center distance <0.55. These are rule thresholds, not mesh bounds. |
| Warnings | Fang windup 0.7 s, dash 0.42 s at 13 units/s; Mire zone radius 2.3, warning 1.3 s then active for 4 s; boss zone radius 5, warning 1.6 s then active for 0.5 s |
| Companion placement | Visual orbit radius 2 for bases, 2.6 for evolved allies; current visual scale 0.85, six places maximum. Simulation attacks are measured from keeper/target, not rendered mesh reach. |
| Content | Six base roles, three first evolutions and three ascensions; recipes and combat values in `src/content.js`; late wave-9 spawn override 18/s, cap 240 |
| Outcome | Boss actual damage/death wins; keeper zero health loses; retry resets state |

Retain the nonblocking observations without labeling them defects: CORE-O1, Worldcoil/Pyre/two-Moth made wave 11 almost empty; CORE-O2, long-range auto-fire made intercepting a desired replacement time-sensitive. The visual plan adds clearer capture reach and ability source cues later, with no free capture or damage changes. Independent pure Dusk/Solar/Eclipse full runs and formal busy-scene profiling remain later QA coverage.

Step-12 files live under `notes/`; they do not replace core runtime geometry or modify the approved source/build.
