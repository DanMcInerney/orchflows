# U8 dogfood: `browser-fps`

What the build spec's U8 asked for, and what actually happened when it ran.
Spec: [`../workflow-ladder-spec-2026-09-02.md`](../workflow-ladder-spec-2026-09-02.md) section 3, U8.

## Where things are

| thing | where |
| --- | --- |
| the two sheets and the glue workflow, verbatim | `ring/` beside this file |
| the ring they were authored and run in | `C:\Users\danhm\.orchflows\b132h` (a scratch home ring) |
| the run's tickets, journals and evidence | `C:\Users\danhm\.orchflows\b132h\state` |
| the game the run built | `C:\Users\danhm\tools\nightfall-crypt`, tip `887868e` |
| captures, three rounds | `...\b132h\state\research\20260903T020000Z-browser-fps\captures*` |

`ring/` is a copy for the record. The items are **not** installed in the live
home ring: see "Why a scratch home ring" below, and "To install them" for the
two commands that put them there once the trunk is current.

## The run

`browser-fps` ran three times. The first two were abandoned on one defect,
found twice at two different call sites; the third closed **complete**.

| run | closed | why |
| --- | --- | --- |
| `20260903T012000Z-browser-fps` | limited | `land`'s `workspace-integrate` said `absent` at exit 0 and merged nothing: the run's integration target had been fixed on the driver's own checkout by the *content* `do`, which named no `--workspace` |
| `20260903T015000Z-browser-fps` | limited | the same defect one call earlier -- `checkpointed-build`'s **plan** step is written without `--workspace`, so the cut child fixed the target on the driver's tree before any wave was minted |
| `20260903T020000Z-browser-fps` | **complete**, done exit 0 | every call names `--workspace`; the target was asserted against the fixture before the first wave |

Both bodies are repaired: the glue's content `do` names `--workspace` and its
`Never` names the failure, and `skills/workflows/checkpointed-build/SKILL.md`
does the same for its plan step. The deeper question -- whether a call that
establishes nothing in a git tree should be able to fix a run's *git*
integration target, and whether `absent` should name the repository it
searched -- is the library's and is logged as friction.

## The third run, call by call

    frame-open --workflow browser-fps                      -> B1  (home ring resolved)
      do  orch-research-pack                               -> B1.2  evidence: the engine
      do  orch-content-pack   --sheet fps-design           -> B1.1  doc: DESIGN.md
      frame-open --workflow checkpointed-build --parent B1 -> B1.3 (library resolved)
        do    orch-code-pack  --makes cut                  -> B1.3.1  the cut
        do    orch-code-pack  --sheet threejs  (isolated)  -> B1.3.2  the tracer     -> ca506bd
        do    orch-code-pack  --sheet threejs  (isolated)  -> B1.3.3  the game       -> d265504
        judge orch-design-pack --sheet threejs             -> B1.3.4  BLOCKED
        do    orch-code-pack  --sheet threejs  (isolated)  -> B1.3.5  repair         -> e60f7ee
        judge orch-design-pack --sheet threejs             -> B1.3.6  holds
      frame-close --done "node .../tests/probe.mjs"        -> B1.3 complete, exit 0
      judge orch-design-pack  --sheet fps-design           -> B1.4   BLOCKED
      do    orch-content-pack --sheet fps-design           -> B1.7   repair (brief)  -> bd1332c
      do    orch-code-pack    --sheet threejs  (isolated)  -> B1.6   repair (budget) -> 887868e
      judge orch-design-pack  --sheet fps-design           -> B1.8   holds
    frame-close --done "node .../tests/probe.mjs"          -> B1  complete, exit 0

`B1.5` is B1.7's first ticket: minted `--isolation required`, refused *after*
sealing by the document-tree adapter, and set `failed`. A content-pack call
cannot be an isolated candidate.

## The probe, at the tip

    node C:\Users\danhm\tools\nightfall-crypt\tests\probe.mjs        exit 0

      drawn: 35.2% of sampled pixels lit
      the level started: phase playing at tick 15
      W for 1.6 s moved the player 3.71 m; the sarcophagus stopped it at z 0.89
      S for 2.2 s brought the player to z 5.58; the wall held
      draw calls: 8
      frame body over 240 frames: p50 0.50 ms, p95 0.90 ms
      pointer-lock refusal message shown
      page errors 0, console errors 0, requests after load 0

Can-fail readings, each taken by mutating the tree and restoring it, so none
of the greens above is an arrival: the forward key ignored gives "W moved the
player 0.00 m"; nothing blocking gives "the player passed through the wall
(z 7.12)"; one mesh per prop instead of an InstancedMesh gives "21 draw
calls, over the brief's bound of 20"; 12 ms of work inside the measured frame
body gives "frame body p95 12.70 ms, over the brief's budget of 8.0 ms".

## What the run proved about the ladder

- **Sheets resolve from a ring and pin.** `--sheet threejs` put
  `sheet_digests: {"threejs":"sha256:cefda2af..."}` on every wave's ticket and
  the sheet line, keyed `### git`, in every launch prompt; the judges read the
  same digest.
- **`packs:` refuses.** `do --pack orch-code-pack --sheet fps-design`
  answered "sheet 'fps-design' declares packs ['orch-content-pack',
  'orch-design-pack'] and this callable stamps 'orch-code-pack'". This is why
  the glue runs its own design judge instead of handing `fps-design` to
  `checkpointed-build`, whose `Never` forbids giving the judge a sheet the
  waves did not carry -- and the waves structurally cannot carry this one.
- **A ring workflow invokes a library workflow as a nested frame.**
  `frame-open --workflow checkpointed-build --parent B1` resolved to
  `skills/workflows/checkpointed-build/SKILL.md`.
- **`orchflows check` is green on the ring** and refuses when it should: a
  bad Lens key gives exit 1; a `tools.txt` inside a sheet is refused.

## Two library defects the run found

1. **`orchflows check` does not report a missing tool.** With `tools.txt`
   naming a tool that is not on the machine, `orchflows sync` says "tools
   workflow 'browser-fps': '...' is not on PATH (tools.txt line 11)" and
   `orchflows check` prints nothing and exits 0. The spec's `tools.txt` row
   fixes both readers.
2. **A `done` predicate cannot name `pnpm`.** `frame-close --done "pnpm run
   probe"` fails with "[WinError 2] The system cannot find the file
   specified": `pnpm` on Windows is a `.CMD` shim and the done runner spawns
   argv without a shell. Every probe here names `node` directly. The same
   `.CMD` cause was repaired at `orchflows_node`'s spawn sites; the done
   runner was not in that scope.

Both, and the integration-target and worktree-retire findings, are logged as
friction.

## Why a scratch home ring

`~/.orchflows/receipt.json` reads source commit `58cb...` -- `main` before
this run -- and the installed trunk has no sheet kind, no `--sheet`, no
`orchflows check` and no `tools.txt`. Installing this candidate over it
mid-run would have swapped the trunk under the run's own sibling agents.
The sink environment variable [`rules/visibility.md`](../../rules/visibility.md)
section 6 names moves the sink and the home ring together
(`state_root.orchflows_home()` is `state_root().parent`), so
`C:\Users\danhm\.orchflows\b132h` is a home ring by every code path the
library has.

## To install them

After the gate reinstalls the library:

    cp -r research/workflow-ladder-dogfood-2026-09-02/ring/sheets/*    ~/.orchflows/sheets/
    cp -r research/workflow-ladder-dogfood-2026-09-02/ring/workflows/* ~/.orchflows/workflows/
    orchflows sync && orchflows check

The host adapters this run's `sync` wrote for the scratch ring were removed
again, so `sync` above is what creates them against the real path.

## Open successors

- `orchflows check` should run the tooling probe (defect 1).
- The done runner should spawn a `.CMD` shim, or the law should say a `done`
  names an executable (defect 2).
- `land`'s `workspace-integrate` `absent` should name the repository and
  branch it looked for; and a non-establishing call should not fix a run's
  git integration target.
- `git worktree remove` refuses on any wave that built node artifacts
  (`node_modules/` present, ignored, not deleted) and has already removed the
  `.git` pointer by then.
- From the game's own judges: the brief's **Esc** row is not bound by the
  build; mouse look is uncovered because pointer lock cannot be granted
  headless; `blocksSight` is exported and read by nothing; the excluded
  mobile breakpoint renders unannounced.
