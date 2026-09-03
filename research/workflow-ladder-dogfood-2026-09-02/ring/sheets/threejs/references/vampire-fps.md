# The shipped slice: what the reference workspace actually does

Source: `C:\Users\danhm\tools\vampire-fps` at 2026-09-03, entry 1 of run
`20260902T150541Z-vampire-fps-build`. Files cited by path in that workspace.

## Static delivery

`README.md`, "Run it": "`npm run build` writes a static `dist/`; serve that
directory from any static file host, at any path, and the game plays. It makes
no network request after the page has loaded." `tests/smoke/game.smoke.mjs`
asserts it: it records every request after load and asserts the list is empty.

## The measurement seam

`tests/smoke/game.smoke.mjs` drives the built page through Chromium and reads
`window.__GAME__.report()` for tick, position, phase, spawns, kills, level and
draw calls, and `window.__GAME__.probe()` for the fraction of sampled pixels
lit. Its own header states the reason: "a renderer drawing nothing passes
every check that does not look at the pixels." The measured figure on that
host is around 0.6 lit before the run and 0.45 during it; the check's bar is
0.2.

The same file asserts `report.drawCalls < 40` with the comment "the batching
is gone", and asserts zero page errors and zero console errors.

## Input, and pointer lock

`README.md`, "Play it": click to begin starts the run and asks for the pointer
lock; WASD or the arrow keys move; the mouse looks. "If the browser refuses
the pointer lock, the game says so in a strip at the bottom of the page and
keeps going — movement, the number keys and the mouse still work, only
relative mouse-look is lost." The smoke check proves both halves: it presses
`KeyW` for 700 ms and asserts the reported position moved more than a metre,
and it dispatches `pointerlockerror` and asserts the in-page notice appears.
