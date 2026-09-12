# Short video

Original humor, personal stories, education and marketing for Shorts, TikTok, Reels or caller-selected placements. The brief and the idea determine duration, cuts, visual language, audio, closing action and renderer.

```text
short-video → make-short-video   → orch-work   → editable project + exports
            → review-short-video → orch-review → findings on those exports
```

The coordinator stays in the caller. N requested films use N makers and N fresh reviewers: 2N agents. Placement versions of one film stay with its pair; every delivered export receives review. Either leaf works alone with one agent. Additional research agents, direction reviews and repair rounds require a caller request.

Quality inherits Writing + Visual design → [Short video](standards/short-video.md) → [Marketing](standards/short-video/marketing.md) when applicable. Brand profiles invoke `short-video:short-video` with product references and a standard extending Marketing. Every ancestor is passed once; profiles add no agents.

## Install and dependencies

From a complete orchflows-light checkout, run `python scripts/orchflows.py setup --example short-video` (Python 3.11+; `python3` where needed). This copies the example once, preserves an existing library and registers it in the home catalogs. Setup installs no media dependencies.

Register the selected home using `codex plugin marketplace add <home>` or `claude plugin marketplace add <home>`. Install `orchflows-light@orchflows-home` and `short-video@orchflows-home` using `codex plugin add` or `claude plugin install … --scope user`, then start a new session. Keep only one core installation enabled. After edits, bump all three manifest versions and refresh the library through the host: Codex `plugin add`; Claude `plugin marketplace update orchflows-home`, then `plugin update short-video@orchflows-home`.

Invoke `$short-video:short-video` in Codex or `/short-video:short-video` in Claude Code. Supply the subject, audience, intent, placements, constraints and output location. [Library context](references/library-context.md) handles path resolution, including standalone leaves and direct file invocation.

Requires native child delegation, orchflows-light's two primitives and Writing/Visual design standards, an available authoring/export toolchain, and access to the exported media. Full audiovisual review requires actual motion viewing and listening capabilities; limited tools yield explicitly partial review. [Remotion](references/remotion.md) is an optional toolchain. Generated projects carry their own dependencies and stay outside this package.

[Trial requests](trials/request.md) and [expected behavior](trials/expected-behavior.md) describe tests to run; they are not results.
