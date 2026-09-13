# Agent-playable test interface

Implement this contract in the generated game when building its foundation. Adapt names to an established project, document the mapping and keep one owner. It is not a requirement to install a particular browser driver. Follow the host browser skill: supported UI interaction always works as the baseline, and page evaluation is used only where the tool permits it.

## Three forms of evidence

| Mode | Control and observation | Establishes |
| --- | --- | --- |
| Ordinary play | Public start/menu, keyboard/pointer/touch, visible game feedback | Actual reachability, usability and player experience |
| Assisted play | Same rules, explicit slow/step mode or semantic action controls, captures after actions | Tactical reasoning and diagnosis, with timing assistance disclosed |
| Scenario/regression | Seed, legal starting fixture, bounded actions and assertions | Reproducible rule/state coverage; not evidence that a player can reach the fixture |

Complete at least one start–play–outcome–retry path through ordinary input for a full game. Use assisted sessions when the browser tool cannot reliably perform an action, but keep any untested real-time control claim unverified. Never teleport to an ending and describe it as a played win.

## Public controls first

Provide usable instructions and named start, pause/resume, restart and settings controls as appropriate. Make canvas focus intentional and give the canvas an accessible name. Expose key UI states through DOM text/roles where practical; essential cues still need to be visible during normal play. A DOM HUD can describe health/objective/cooldowns without revealing hidden enemies or a puzzle solution.

At the capability probe, prove press-and-release, a held movement/action, mouse or camera input and pause/resume with the actual browser tools. If pointer lock is unsupported, provide a development look panel or equivalent supported action path and document what ordinary camera testing remains unavailable. Do not change an FPS into a different genre to accommodate a tool limitation.

## Development controls

Implement a small versioned adapter, for example `window.__gameTest`, only in a local development/test build. Also expose its operations as labeled DOM controls when programmatic calls are unavailable. The DOM panel must be sufficient to select a scenario/seed, reset, release inputs, choose live/manual mode, issue a legal action, advance a bounded number of ticks and read status. Both adapters call the same functions; neither owns a second simulation.

| Operation | Semantics |
| --- | --- |
| `describe()` | Adapter version, supported actions and ranges, coordinate units, scenarios, fixed tick duration, build ID and readiness/error state |
| `snapshot()` | Serializable copy of the current observable state; no live object references or setters |
| `reset({seed, scenario})` | Clear queued/held input, timers, entities, outcome, random state and transient UI; load a known legal fixture and render it |
| `setMode('live' \| 'manual')` | Explicitly choose the clock owner; switching clears accumulated time and pending held input |
| `act(action)` | Queue a validated semantic input through the ordinary action dispatcher, with explicit press/release or bounded duration |
| `step(ticks)` | In manual mode only, advance an integer in a documented safe range, then render; fail in live mode |
| `releaseAll()` | Clear held actions, including after test failure, blur or session cleanup |

`reset` and asset readiness may be asynchronous. Expose loading/ready/error status and wait for completion before accepting actions or stepping. Bound durations and validate names/numbers to reject invalid work rather than hanging the browser. Pausing and stepping must have documented semantics: the adapter may set manual simulation mode, but must not accidentally bypass a player's paused-menu state or an ended session.

A useful snapshot contains build/scenario/seed/tick, mode and phase, player transform/velocity, currently visible entities with stable IDs and useful states, objective progress, resources/cooldowns, current input intent, recent events, and load/error status. Define position axes and units. Keep diagnostic information that reveals hidden state separately labeled, and do not use it for an uncoached or player-equivalent play claim. Have an event tail such as interaction accepted/rejected, resource spent, damage/setback, objective completed and session ended so silent bugs have an explanation.

Record scenarios as data using the real simulation initializer. A fixture can begin at a late-game situation for QA, but the same rule system must decide collisions, opponent responses and outcomes. Preserve an ordinary path through the actual level progression. If complete deterministic replay is infeasible, use stable seeds and approximate assertions with recorded tolerances; do not promise bitwise agreement across machines.

## Production and adapter verification

The normal release keeps public controls and omits state-changing development hooks, fixture menus and overlays. If using a separate test build, generate both from the same source/configuration for gameplay and assets; only diagnostics differ. Record both identities. An opt-in URL alone is not a production isolation boundary if cheats must be absent from the release. Final ordinary play and performance run on the actual production candidate.

Verify the interface before relying on it:

1. Reset the same scenario/seed twice, apply the same bounded actions and compare observable outcomes within the declared tolerance.
2. Hold manual mode without stepping and confirm simulation tick/state do not advance; step a known number and confirm exactly that advance and a changed render when the action calls for it.
3. Trigger a representative action with ordinary browser input and the adapter from the same starting state. Confirm the same rule/event outcomes, accounting for live timing.
4. Trigger blur/pause/restart and confirm held input is cleared, only one loop remains and a new session has fresh state.
5. Verify the production build boots with required assets and its ordinary controls work with diagnostic hooks/panel absent.

These checks belong in the generated project using its available test runner. They validate actual behavior, not merely that named functions exist. Browser input semantics and supported actions depend on the driver; consult its [official input documentation](https://playwright.dev/docs/input) when using standalone Playwright, and the host's own documented API when using an in-app browser.
