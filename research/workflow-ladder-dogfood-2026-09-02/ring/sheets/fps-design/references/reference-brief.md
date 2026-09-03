# The one brief this sheet was written from

Source: `C:\Users\danhm\tools\vampire-fps`, run `20260902T150541Z-vampire-fps-build`
entry 1, read 2026-09-03. It is the only shipped first-person browser game
this library has evidence for, so every clause in the sheet traces to a
sentence in it or to a defect it exposed.

## What its README fixes, and how

`README.md` opens with the shape in one paragraph: "Twenty minutes in one
arena, a weapon that fires by itself at whatever you are looking at, waves
that never stop, and one upgrade every level." One arena, a fixed duration,
and the loop — the level, the time and the goal are all stated before any
mechanic is.

Its "Play it" section is a table, one row per control: click to begin;
**W A S D** or the arrow keys to move; the mouse to look ("Looking is
aiming"); **1 2 3** or a card click to take an upgrade; **Esc** to release
the cursor; **`** to toggle the stats overlay. The mouse has its own row and
its own sentence. This is the shape the sheet's input clause asks for.

Pointer lock is written as a stated failure, not an assumption: "If the
browser refuses the pointer lock, the game says so in a strip at the bottom
of the page and keeps going — movement, the number keys and the mouse still
work, only relative mouse-look is lost." The README then names the decision
this constrains, `decision:delegated.Q-01.target-device-cohorts`, desktop
only, "because Pointer Lock is the only route to relative aiming".

## What was out, and where it was said

The README's closing section names each thing the slice does not do and which
successor entry owns it — budget measurement, launch content, the beauty
pass, the promised affordances, release — against
`program/successor-plan.md`. The absences are enumerated rather than left to
the reader, which is what the sheet's exclusions clause asks for.

## What the build measured rather than described

`tests/smoke/game.smoke.mjs` asserts figures, not adjectives: the player
moved more than a metre after 700 ms of `KeyW`; more than 0.2 of sampled
pixels were lit; fewer than 40 draw calls; zero console errors. A brief whose
feel is an adjective cannot be checked this way, which is why the sheet asks
for metres per second and a frame budget.

## The defect that produced the "one vertical slice" clause

That build run is recorded as PAUSED after entry 1 landed, with the resume
recipe in its frame journal: the brief covered six entries and one was built.
A brief whose body describes states the first load never reaches leaves the
maker choosing which sentences apply.
