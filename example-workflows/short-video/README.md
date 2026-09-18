# Short video

**Make something worth watching twice.**

Turn a brief into an original short film, an editable project and actual rendered exports. Then a fresh reviewer examines those exact files: the opening, the payoff, the pacing, the captions and the sound where playback tools allow it.

Use it for a joke with a reveal, an explanation that finally clicks, a personal story or a product demonstration with something to prove. The [video guidance](guidance/short-video.md) asks each film to earn its audience's attention and fulfill the promise of its hook. [Marketing guidance](guidance/short-video.marketing.md) adds product relevance and evidence for claims when the brief calls for it.

## Try it

After installation, paste into Codex:

```text
$short-video:short-video
Create a 25-second animated explanation of why the Moon has phases for
curious beginners. Open with a visual puzzle and resolve it with a clear
demonstration. Deliver 9:16 and 1:1 versions with readable captions in
./moon-phases, plus the editable project and render instructions.
Use silence intentionally; no narration or music.
```

In Claude Code, use `/short-video:short-video` with the same brief. All skills in this library are manual-only by default.

Supply the subject, audience, intent, placements, constraints and output location. Include assets and supporting facts when they matter. Unspecified creative choices are made for the brief; different films receive separate output locations.

## Production, then independent review

```text
Brief → maker → editable project + rendered exports
                  ↓
            fresh reviewer → timestamped findings + coverage gaps
```

The orchestrator chooses production and review assignments. Independent films can proceed concurrently; each completed film receives independent review of all its placements and overall coherence.

The maker takes the film from concept through export and checks the result. The reviewer receives the original brief and the exact exports, identified by path and SHA-256, then reports findings without changing them. The full workflow adds no separate research stage, outline review, extra coordinator or repair loop. Further work requires your request.

| Choose a skill | What it does |
| --- | --- |
| [short-video](skills/short-video/SKILL.md) | Make films and independently review their exports. |
| [make-short-video](skills/make-short-video/SKILL.md) | Produce an editable film and exports without an independent review. |
| [review-short-video](skills/review-short-video/SKILL.md) | Review existing exports independently without repairs; prior use of the maker is unnecessary. |

## Keep the film and the project

Delivery includes editable source and available assets, playable exports, file identities, instructions to reopen and render, independent findings and remaining gaps. Review states what was decoded, inspected as frames, watched in motion and heard. Full review requires motion viewing and listening when sound is present; limited tools produce partial review with the unobserved parts named.

Brand profiles can call `short-video:short-video` with product references, guidance names and package roots. Dotted guidance such as `short-video.marketing.orchflows` adds brand preferences. [Library context](references/library-context.md) owns the shared dependency and guidance rules.

## Install and requirements

From a complete orchflows core checkout, with Python 3.11+:

```sh
python scripts/orchflows.py setup --example short-video
```

Setup copies the example into your orchflows home, preserves existing library copies and installs no media dependencies. Follow core `docs/hosts.md` to register and install `short-video@orchflows-home`, then start a new session. Core `docs/home.md` covers updates.

Requires orchflows 0.10.0+, native child delegation, an authoring/export toolchain and access to the exported media. [Remotion](references/remotion.md) is optional; generated projects carry their own dependencies in the caller's workspace. Full audiovisual review also needs motion viewing and, for films with sound, listening capabilities.

The [trial requests](trials/request.md) and [expected behavior](trials/expected-behavior.md) describe repeatable validation, not observed results or a promise of popularity.
