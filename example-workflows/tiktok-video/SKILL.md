---
name: tiktok-video
description: Make one 1–120s TikTok marketing video for anything — cited brief, judged hook variants, rendered 9:16 with burned captions.
disable-model-invocation: true
---

Require: `subject`, what is being marketed and every asset it comes with
(URL, screenshots, footage, logo); `goal`, one of awareness, traffic or
conversion; `length`, the target seconds inside 1–120; `brand`, the voice
contract plus visual tokens, or `none`; `workspace`, the git-backed render
project, or `new`; `keys`, the provider keys on hand, or `none`. Every
call reads [the rules](references/tiktok-video-rules.md); the render
call also reads [the pipeline](references/tiktok-video-pipeline.md).

    tickets.py frame-open <run> --goal-file <video-goal> --workflow tiktok-video

Re-read the frame's `## Report` and its children before each call, then
append the decision with `tickets.py result <run> <frame> --by <frame>`.
Keep every returned `artifact:` and `findings:` line verbatim; the next
call is handed the line itself.

**Brief**, `do --pack orch-research-pack --bound "<= 40 tool calls"`: one
evidence packet for `subject` — audience and its stated pains, proof
points, the hooks and formats competitors run on TikTok now, sounds and
trends live in the niche — every claim cited and dated, gaps declared.

**Scripts**, `do --pack orch-content-pack` handed the brief's artifact
line: one document holding three scripts for `length` and `goal`, each a
beat sheet from a different hook archetype the rules name — timed beats,
voice lines, on-screen text, shot list, sound, one CTA — plus a six-second
cutdown of the strongest.

**Script judge**, `judge --pack orch-content-pack` over that document: a
verdict per script against the rules' hook, structure and CTA checks,
ranked, blocks named. One repair `do` covers only named blocks, then this
judge runs once more; two rounds is the bound.

**Render**, `do --pack orch-code-pack --isolation required` in `workspace`,
handed the passing scripts and `keys`: the pipeline's project — voice,
word-timed captions, footage or generated shots, music under the voice —
every passing script rendered to its 1080×1920 MP4 with cover frame,
contact sheet, captures and the spec probe the pipeline defines, that
probe the call's `done`.

**Render judge**, `judge --pack orch-design-pack` over the render's
`git:` line: the captures against the rules' safe zones, caption
legibility, brand tokens and pacing; one verdict per variant. Blocks earn
one repair `do --pack orch-code-pack` and one re-judge, then the frame
closes on what passed.

Never: open on a logo, slate or silence; carry text into a zone the
TikTok UI covers; render a script the judge did not pass; export outside
9:16 at 1080×1920; substitute a paid provider `keys` does not name; or
close on the renderer's own claim.

Return: `tickets.py frame-close <run> <frame> --done <probe>`, whose done
is the spec probe over every delivered MP4 run outside the render — codec,
frame size, duration inside `length`, loudness, captions present — as an
exit code, beside the render judge's verdict per variant.
