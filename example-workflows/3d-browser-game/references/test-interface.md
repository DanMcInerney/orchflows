# Agent-playable test interface

Implement with the foundation. Adapt names to an existing project, document their mapping and keep one owner. Follow the host browser skill: supported UI is the baseline; use page evaluation only when permitted. No particular driver is required.

## Evidence modes

| Mode | Controls/observations | Establishes |
| --- | --- | --- |
| Ordinary | Public menus, keyboard/pointer/touch, visible feedback | Reachability, usability, player experience |
| Assisted | Same rules, explicit slow/step or semantic actions, action captures | Tactical reasoning/diagnosis with disclosed timing assistance |
| Scenario/regression | Seed, legal fixture, bounded actions/assertions | Reproducible rule/state coverage, not fixture reachability |

A full game needs an ordinary-input start–play–outcome–retry path. Use assistance for actions tools cannot reliably perform; untested real-time controls remain unverified. Teleporting to an ending is not a played win.

## Public controls

Provide instructions and named start, pause/resume, restart and settings as applicable. Make canvas focus intentional and name it accessibly. Expose useful UI text/roles while preserving visible essential cues; DOM health/objective/cooldowns must not reveal hidden enemies or solutions.

Probe actual press/release, held action/movement, mouse/camera and pause/resume. If pointer lock is unsupported, provide a development look panel or supported equivalent and identify missing ordinary camera tests. Do not change genre to fit tool limitations.

## Development adapter

Provide a small adapter, e.g. `window.__gameTest`, only in local development/test builds. When programmatic calls are unavailable, expose equivalent labeled DOM controls. Both call the same functions, never a second simulation. The panel must select scenario/seed, reset/release inputs, select live/manual mode, issue legal actions, advance bounded ticks and show status.

| Operation | Contract |
| --- | --- |
| `describe()` | Actions/ranges, coordinate units, scenarios, fixed tick duration, build ID, readiness/errors |
| `snapshot()` | Serializable observable-state copy; no live references/setters |
| `reset({seed, scenario})` | Clear queued/held input, timers, entities, outcome, random state and transient UI; load/render a legal fixture |
| `setMode('live' \| 'manual')` | Choose clock owner; clear accumulated time and pending held input |
| `act(action)` | Validate/queue semantic input through ordinary dispatch with press/release or bounded duration |
| `step(ticks)` | Manual only: advance an integer in a documented safe range and render; fail in live mode |
| `releaseAll()` | Clear held actions after failure, blur or cleanup |

Expose asynchronous reset/asset loading as loading/ready/error; wait before actions/steps. Validate names/numbers and bound durations. Document pause/step semantics; manual mode must not accidentally bypass paused menus or ended sessions.

Snapshots include build/scenario/seed/tick, mode/phase, player transform/velocity, visible entities with stable IDs/states, objectives, resources/cooldowns, input intent, recent events and loading/errors. Define axes/units. Label hidden diagnostics separately and exclude them from uncoached/player-equivalent claims. Include event tails for accepted/rejected interactions, spending, setbacks, objectives and session end to explain silent bugs.

Store scenarios as data for the real initializer. Late-game fixtures still use normal collision, opponents and outcomes; preserve ordinary progression. If exact replay is infeasible, use stable seeds and recorded assertion tolerances, not promises of cross-machine bitwise agreement.

## Production and verification

Release builds retain public controls and omit state-changing hooks, fixture menus and overlays. Test builds share gameplay/asset source and configuration; only diagnostics differ. Record both identities. An opt-in URL alone cannot isolate production cheats. Final ordinary play and performance use the actual production candidate.

Verify behavior with the project's available runner:

1. Reset the same seed/scenario twice; compare identical bounded actions within declared tolerances.
2. Hold manual mode without stepping: ticks/state must remain fixed. Step a known count: exactly that advance and an appropriately changed render must follow.
3. Compare ordinary browser input and adapter actions from the same state; rule/events must match, allowing live timing.
4. Blur/pause/restart must clear held input, retain one loop and create fresh session state.
5. Production must boot with required assets and ordinary controls, without diagnostics.

Function existence alone proves none of this. Use [official Playwright input docs](https://playwright.dev/docs/input) for standalone Playwright or the host's documented in-app API.
