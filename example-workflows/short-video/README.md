# Short video

Turn a brief into an original short film, editable project and rendered exports. A fresh reviewer examines those exact files for opening/payoff, pacing, captions and sound, within available playback capabilities.

## Try it

```text
$short-video:short-video
Create a 25-second animated explanation of Moon phases for curious beginners.
Open with a visual puzzle and resolve it clearly. Deliver 9:16 and 1:1
versions with readable captions in ./moon-phases, plus editable source
and render instructions. Use intentional silence; no narration or music.
```

Claude Code: `/short-video:short-video`. Skills are manual-only by default. Supply subject, audience, intent, placements, constraints, output location, assets and supporting facts. Unspecified creative choices follow the brief.

## Process and results

| Skill | Result |
| --- | --- |
| [short-video](skills/short-video/SKILL.md) | Production followed by independent review of every film's exports |
| [make-short-video](skills/make-short-video/SKILL.md) | Editable project and actual exports; no independent review |
| [review-short-video](skills/review-short-video/SKILL.md) | Independent review of existing exports; no repairs or prior-maker requirement |

The coordinator chooses assignments. Independent films can run concurrently in separate output locations; each review covers every placement and overall coherence. Reviewers receive the original brief and stable exports identified by path/SHA-256. The workflow adds no research gate, outline review or repair loop; further work requires your request.

Delivery includes source/assets, playable exports and identities, reopen/render instructions, timestamped findings and gaps. Reviews distinguish decoding, frame inspection, watched motion and heard audio. Full audiovisual acceptance requires motion viewing and listening when sound exists; missing capabilities produce partial review.

[Video guidance](guidance/short-video.md) addresses genre, audience and earned payoff; [marketing guidance](guidance/short-video.marketing.md) adds product relevance and supported claims. Brand profiles may compose this workflow with product references, package roots and dotted guidance such as `short-video.marketing.orchflows`. [Library context](references/library-context.md) owns dependencies and selection.

## Install

From a complete Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example short-video
```

Setup preserves existing library copies and installs no media dependencies. Follow core `docs/hosts.md` for registration/installation and start a new session; use `docs/home.md` for updates.

Requires core 0.11.0+, native child delegation, authoring/export tools and exported-media access. [Remotion](references/remotion.md) is optional; project dependencies stay in the caller workspace. Full review requires motion viewing and applicable listening.

[Trial requests](trials/request.md) and [acceptance](trials/expected-behavior.md) specify validation, not observed results or popularity guarantees.
