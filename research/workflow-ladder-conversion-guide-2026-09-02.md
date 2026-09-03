# The ladder, in plain English (2026-09-02)

This is the human-readable half of the workflow-ladder design. The half a run
carries is `research/workflow-ladder-spec-2026-09-02.md`. The design itself is
"One Interpreter, Two Verbs" (https://claude.ai/code/artifact/41d1015e-19d0-4287-a88b-c868b0a35ad3).

## The idea in one paragraph

A workflow is a program that the session you are talking to reads and runs,
one line at a time. Only two things ever run somewhere else: `do` (make one
thing) and `judge` (read one thing and say what is wrong), each in a fresh
context with a pack's craft. Everything you want to reuse is one of four
kinds, and each kind has a different price. A **script** costs a function call.
A **callable** costs a fresh context. A **workflow** costs a frame. **Knowledge**
costs nothing to run and is where nearly all the specificity should go. The
skill you type (`/browser-fps`) is a hundred and fifty words that names parts
from a library and pins their parameters. The parts do not know what game you
are building. The prompt does.

## How to read the flowcharts

    [root]              a command the root runs itself; no child, no model spend
    (do · pack)         a child that makes one artifact through that pack's craft
    <judge · pack>      a child that reads a fixed artifact and returns findings
    {sheet}             knowledge pinned to a ticket at one digest, read by maker and judge
    frame ▸ name        a reusable workflow, opened as its own frame under this one
    ──►                 the typed line handed to the next step, word for word
    ⟲ ≤2                bounded repair: one repair do, one re-judge, two rounds is the bound
    ∥                   launched together

## The four questions

Ask them in order about any step. The first yes decides the rung.

1. **Does no model need to judge anything here?** Then it is a **script**. A
   fetcher, a renderer, a validator, a probe. Put it in a skill's `scripts/`
   or make it a ticket's `script:` executor. It costs milliseconds and it is
   testable.
2. **Does it need its own context** (isolation, a lease, a landing that
   survives a crash, eyes that did not make the thing)? Then it is a
   **callable**: `do` or `judge` with a pack. If the pack's craft cannot carry
   the method (an API roster, a manifest format), give the callable an
   **applied skill** with `--skill`. If the pack's craft is too broad
   (code, when you mean three.js), give it a **sheet** with `--sheet`.
3. **Does it hold at least one callable and recur across workflows**, or
   deserve its own journal? Then it is a **reusable workflow**, invoked by
   name as a nested frame. Its parameters are `Require` items the caller fills
   in a goal file.
4. **None of the above?** It is a **sentence** in the caller's prose. If the
   sentence recurs, its wording is an **idiom** owned once in the authoring
   doc and quoted verbatim.

And one question that is not about a step at all: **is this knowledge, not
action?** Then it is the prompt (true for this run only), a sheet (true for a
narrow domain), or a pack (true for an artifact kind). Never a step.

## Conversion 1: tiktok-video

**Before.** A 461-word body, all serial, with two thousand words of TikTok
knowledge in two reference files that the children read through goal files.

    /tiktok-video <brief>
    [root] frame-open --workflow tiktok-video
      (do · research)     audience, pains, competitor hooks, live sounds    ──► doc: brief
      (do · content)      three scripts + a 6 s cutdown                     ──► doc: scripts
      <judge · content>   scripts against tiktok-video-rules.md   ⟲ ≤2      ──► findings
      (do · code)         render every passing script, isolated worktree   ──► git: mp4 set
      <judge · design>    safe zones, captions, pacing           ⟲ ≤2      ──► findings
    [root] frame-close --done probe
    body 461 words · references 1,987 words · 5 children · 2 gates

**After.** The two reference files were already sheets; they just were not
pinned, and the maker and the judge were not mechanically reading the same
bytes. The render-judge-repair tail is the same shape as paper-repro's and the
FPS build's, so it becomes a reusable workflow.

    /tiktok-video <brief>
    [root] frame-open --workflow tiktok-video            ← the trunk prints the frame law here
      (do · research {market-brief})                    ──► doc: brief
      (do · content {tiktok-script})                    ──► doc: scripts
      <judge · content {tiktok-script}>     ⟲ ≤2        ──► findings
      frame ▸ checkpointed-build
          goal: render every script the judge passed
          pack: code · judge-pack: design · sheets: [tiktok-render]
          probe: the spec probe
                                                        ──► git: mp4 set · findings
    [root] frame-close --done probe
    body ~180 words · sheets: market-brief (shared), tiktok-script, tiktok-render

| what | where it goes | why |
|---|---|---|
| the brief step | a `do` with the shared `market-brief` sheet | one callable, no recurrence of its own; the knowledge is what recurs |
| hook archetypes, script rules, blocking list | sheet `tiktok-script`, read by the scripts maker and the scripts judge at one digest | knowledge two tickets must read identically |
| safe box, caption legibility, pacing, tool table | sheet `tiktok-render`, read by the render waves and the design judge | same |
| render → judge → repair → probe | `checkpointed-build` | holds callables, recurs in three workflows |
| the ledger paragraph | gone; `frame-open` prints it | one owner |

What you gain: the TikTok rules can be improved once and every run picks up
the new digest; the render pipeline's bugs get fixed in one workflow that the
FPS build also uses; the body is a third of its size and every remaining
sentence is about TikTok.

## Conversion 2: super-research

**Before.** The workflow reaches its own skill by writing the skill's resolved
path into the goal file, and the report step describes a self-contained HTML
dossier in prose.

    /super-research <question>
    [root] frame-open --workflow super-research
      (do · research)  × one per source ∥   each child enters the skill by a path in its goal   ──► evidence: ids
      <judge · research>   coverage: which sub-questions no record answers      ⟲ ≤2            ──► findings
      (do · content)       one self-contained HTML dossier, five report rules                    ──► doc: dossier
    [root] frame-close --done verifier

**After.** The skill becomes a pinned field. The dossier rules become a sheet
that paper-repro's site and any future report can stamp too.

    /super-research <question>
    [root] frame-open --workflow super-research
      (do · research --skill research-acquire)  × one per source ∥                    ──► evidence: ids
      <judge · research>   coverage                                    ⟲ ≤2           ──► findings
      (do · content {html-dossier})                                                    ──► doc: dossier
    [root] frame-close --done verifier

The skill gets renamed from `super-research` to `research-acquire` because two
ring items with one name in two kinds is the adapter collision that has been
open since the rebuild. The workflow keeps the name people type. The Python
package inside the skill keeps its name; only the folder and the adapter move.

## Conversion 3: paper-repro

**Before.** Two independent make-judge-repair loops, one for the numbers and
one for the site, each written out in full.

    /paper-repro <paper>
    [root] frame-open --workflow paper-repro
      (do · research)      intake: paper, code, data, headline claim, tolerance     ──► intake line
      (do · code)          reproduce, isolated, bounded                              ──► git: results + figure
      <judge · data>       numbers within tolerance                     ⟲ ≤2         ──► findings
      (do · design)  ∥     static site                                               ──► git: site
      <judge · design>     the site, rendered                           ⟲ ≤2         ──► findings
    [root] frame-close --done probe

**After.** Both loops are the same reusable workflow with different packs and
sheets. The body says what a paper reproduction is; it no longer says how a
build loop goes.

    /paper-repro <paper>
    [root] frame-open --workflow paper-repro
      (do · research {paper-intake})                                                 ──► intake line
      frame ▸ checkpointed-build   ∥   frame ▸ checkpointed-build
          goal: reproduce the headline claim      goal: a static site of the results
          pack: code · judge-pack: data           pack: design · judge-pack: design
          sheets: [paper-repro-rules]             sheets: [paper-repro-visualization, html-dossier]
          probe: the re-run probe                 probe: the site probe
    [root] frame-close --done probe

## Conversion 4: the new one, browser-fps

There is no browser-fps workflow today. The existing `browser-game` is an
intake protocol for incomplete briefs and contains no game craft at all. The
glue workflow for an FPS is small because every heavy part already exists or
is a sheet.

    /browser-fps a one-room vampire-themed browser FPS, keyboard and mouse, static site
    [root] frame-open --workflow browser-fps                                  frame 1
      (do · research)                the engine that fits this brief, with evidence     ──► evidence: engine
      ∥ (do · content {fps-design})   the game design brief                              ──► doc: brief
      frame ▸ checkpointed-build                                                         frame 1.1
          context: evidence: engine · doc: brief
          pack: code · judge-pack: design
          sheets: [threejs] on the waves · [fps-design] on the judge
            (do · code --makes cut)                 a sealed cut of build waves
            (do · code {threejs}) × waves ∥         isolated worktrees
            <judge · design {fps-design}>  ⟲ ≤2     the rendered build
          probe: the site loads, a level starts, input moves the player
                                                                              ──► git: playable build · findings
    [root] frame-close 1 --done <playable probe>

Two levels of prose, one interpreter: the glue body (frame 1), one reusable
workflow (1.1), and callables. Nothing here names an item outside the library,
and nothing asks a child to spawn a child, which is why it runs on a fresh
install and on Codex and Grok too. If `super-research` is installed, the
glue may name it for the engine step instead of the bare research `do`.

**The body, roughly.**

    ---
    name: browser-fps
    description: Build a browser first-person shooter from a one-line brief to a playable static site.
    disable-model-invocation: true
    ---
    Require: `brief` (the game in one paragraph), `workspace`, `bound`.

    Open the frame. In one wave launch `do --pack orch-research-pack` for the
    engine that fits this brief, with evidence, bounded, and `do --pack
    orch-content-pack --sheet fps-design` for the design brief. Hand the
    `evidence:` and `doc:` lines to `checkpointed-build` with the code pack on
    the waves and `threejs` stamped, the design pack and `fps-design` on the
    judge, and the playable probe as its probe. Close on that probe.

    Never: pick an engine the evidence did not rank; build before the brief
    exists; close on the build child's own claim.

    Return: `tickets.py frame-close <run> <frame> --done <playable probe>`, the
    build's `artifact: git:` line and the last `findings:` line.

Everything three.js-specific lives in the `threejs` sheet. Everything about
what makes an FPS feel right lives in `fps-design`. Neither of those is a
workflow and neither is a skill.

## Conversion 5: where the reddit-scraper idea lands

The pyramid is right; the boundary kind was wrong.

    Skill pyramid (every part a context)          Recommended (one context, functions inside)

    reddit-scraper · skill                        research-acquire · applied skill · one do child
      ├─ fetch-comments · skill                     └─ scripts/
      │    └─ parse-thread · skill                        ├─ adapters/reddit.py
      └─ fetch-posts · skill                              ├─ adapters/hn.py
                                                          ├─ adapters/youtube.py
    each hop: a launch, a craft read,                     └─ … 25 adapters, 35 test files
    a lease, a relay · minutes ·
    non-deterministic · forbidden on                 each hop: a function call · milliseconds ·
    Codex and Grok (depth 1)                         deterministic · testable

The one skill boundary buys the thing only a skill buys: a fresh context that
plans manifests and judges coverage. Everything under it needs no model, so it
is code. This is what the super-research rebuild already built.

## What does not change

- **skill-tournament** is already the ladder: a glue workflow that opens
  `benchmaker` and `evolve` as frames and issues no `do` of its own. It is the
  proof the runtime supports all of this today.
- **benchmaker** and **evolve** are engines with their own protocols. `bakeoff`
  is a small sibling of evolve's blind scoring, not a replacement.
- **renovate**, **drift-canary**, **self-improve** keep their steps and lose
  the ledger paragraph. Each gets seventy to ninety words back.
- **browser-game** keeps its steps. Its name says game; its content is a
  brief-intake protocol. A `program-record` sheet and an honest name are a
  successor.
- **A workflow that builds workflows** from one sentence is deferred. Until
  it exists, a new workflow is authored the way U8 authors `browser-fps`:
  sheets by content `do`s stamped `sheet-craft`, the glue body by hand or by a
  content `do`, a judge against the composition law, then `orchflows sync`.

## Where dependencies go

Three classes, three homes, and they never share an environment.

    an item's own Python tooling      requirements.txt beside the manifest   -> ~/.orchflows/envs/<kind>/<name>/  (orchflows sync builds it)
    an item's non-Python tooling      tools.txt beside the manifest          -> checked, never installed; sync and check report what is missing
    an item's Node tooling            package.json + lockfile beside it      -> the item's node_modules/ (sync runs the lockfile install)
    the artifact's dependencies       the workspace's own package.json       -> the child's worktree; lockfile committed with the artifact

For browser-fps: three.js and vite are the artifact's, so they live in the
game's `package.json` in the worktree and orchflows never sees them. The
playable probe is a Python script in the glue workflow with playwright in its
`requirements.txt`, so it gets its own environment. Node and pnpm are tools the
glue workflow declares in `tools.txt`, so `orchflows sync` tells you before the
run if they are missing. A sheet never carries any of this: "use pnpm and node
20" is a sentence in the `threejs` sheet's Craft, and the check lives in
`tools.txt`.

    ~/.orchflows/workflows/browser-fps/
    ├── SKILL.md
    ├── tools.txt            node >= 20 :: node --version
    │                        pnpm :: pnpm --version
    ├── requirements.txt     playwright==1.47.0
    └── scripts/probe.py     runs through `orchflows env workflow browser-fps`

What can go wrong, and what happens: no network at sync, the environment build
fails and sync names the item and the remedy; an untrusted project bundle with
dependencies is skipped until you `orchflows trust` it; two items pinning
different versions never conflict because each has its own environment; a
missing API key is declared as `env NAME` in `tools.txt` and reported by name,
never printed; parallel build waves share pnpm's store, so ten worktrees cost
one download.

## What a sheet looks like

    ---
    name: market-brief
    description: What a cited, dated market brief for a product carries, and what proves it.
    packs: [orch-research-pack]
    ---
    ## Craft
    Name the audience in one sentence and their three sharpest pains, each with
    a quoted source. Name at least three competitors and the hook each leads
    with. Name what is live this window: sounds, formats, phrasings. Date every
    claim. Say which of these you could not find.

    ## Lens
    ### evidence
    Every claim carries a source and a date inside the window. The competitor
    set has three or more entries with a quoted hook each. A gap is written as
    a gap. Blocking: an undated claim; a competitor without a hook; a window
    not named.

Two tickets stamp it: the brief maker and, if the workflow judges the brief,
the brief judge. Both read the same digest. Improve the sheet and every later
run improves with it.

## What a goal file for a nested workflow looks like

The caller fills the reusable workflow's `Require` items in the goal file it
opens the frame with. For `checkpointed-build` inside tiktok-video:

    ## Goal
    Every script the judge passed is rendered to its final variant set.

    ## Context
    - parent: 1
    - artifact: doc:<path>@sha256:<digest>          ← the passed scripts, relayed verbatim
    - findings: <path>                                ← the judge's findings, relayed verbatim
    - pack: orch-code-pack
    - judge-pack: orch-design-pack
    - sheets: [tiktok-render]
    - probe: `uv run --no-project python probe.py`
    - bound: <= 60 tool calls
    - workspace: <tree>

    ## Details
    One variant per script: mp4, cover, contact sheet, captures at 0 s, 1 s, 3 s
    and every beat's first frame, probe.json.

Then `tickets.py frame-open <run> --goal-file <that> --workflow checkpointed-build --parent 1`.

## What you will type, and what you will see

    /browser-fps a one-room vampire-themed browser FPS, keyboard and mouse, static site

The root names the lane, opens frame 1, and the trunk prints the frame law
and the workflow's path. You see frame 1.1 open for the engine question and a
brief child launch beside it. When both typed lines are in the journal, frame
1.2 opens; a plan child seals a cut; wave children run in parallel worktrees;
a design judge reads the rendered build against the FPS sheet; at most two
repair rounds; then the probe runs outside every child and the frame closes.
`orchflows resume` lists any frame that is still open if the session dies.

What is different from today is not what you see. It is that the next game
workflow is a hundred and fifty words, and the render bug you fix for TikTok
is fixed for it too.
