---
name: browser-fps
description: Build a one-room first-person browser game from a brief - engine evidence, a design brief, checkpointed waves, and a playable probe.
disable-model-invocation: true
---

Require: `brief`, the game in a paragraph; `workspace`, the repository the
build cuts from; `probe`, the command that plays the built site; `bound`,
each call's budget.

    tickets.py frame-open <run> --goal-file <brief> --workflow browser-fps

`fan-out`, both launched together:

    tickets.py do <run> --pack orch-research-pack --parent <frame>
      --bound <bound> --goal-file <engine-goal>
    tickets.py do <run> --pack orch-content-pack --parent <frame>
      --sheet fps-design --workspace <workspace> --goal-file <design-goal>

The first names the engine that fits `brief`, every claim sourced and dated.
The second fixes level, input, feel and what blocks.

Then `checkpointed-build` under this frame, its Require filled from both
returned lines: `pack` orch-code-pack, `judge-pack` orch-design-pack,
`sheets` `[threejs]`, and this workflow's `workspace`, `probe` and `bound`.

    tickets.py frame-open <run> --goal-file <build-goal>
      --workflow checkpointed-build --parent <frame>

One design judge over the tip it returns, carrying the sheet a code-pack
wave may not:

    tickets.py judge <run> --pack orch-design-pack --parent <frame>
      --sheet fps-design --artifacts git:<tip> --goal-file <judge-goal>

`bounded-repair`.

Never: stamp `fps-design` on a code-pack call, which its `packs:` refuses;
let a call default its workspace, which silently fixes the run's
integration target; close on a claim.

Return: `outside-close` - `tickets.py frame-close <run> <frame> --done
<probe>` over the returned tip, `artifact: git:<tip>` and the judge's
`findings:` line relayed verbatim.
