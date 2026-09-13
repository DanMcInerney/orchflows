# Short video

Create original short films from a brief, then independently review the rendered exports.

```text
short-video → make-short-video   → orch-work   → editable project + exports
            → review-short-video → orch-review → findings on those exports
```

N films use N makers and N fresh reviewers: 2N agents. Placement versions share their film's pair; every export receives review. Either leaf works alone with one agent. Extra stages or repair rounds require a request.

## Structure

| Owner | Responsibility |
| --- | --- |
| `skills/` | Composition, making and review; built on core's two primitives |
| [Library context](references/library-context.md) | Shared dependencies, guidance selection and paths |
| [Video guidance](guidance/short-video.md) | Production and review criteria; [marketing](guidance/short-video.marketing.md) adds campaign criteria |
| `references/` | Optional toolchain and source context |
| `trials/` | [Requests](trials/request.md) and [expected behavior](trials/expected-behavior.md), not observed results |

Brand profiles call `short-video:short-video` with product references, guidance names and package roots. They add no agents; dotted guidance such as `short-video.marketing.orchflows` adds brand preferences.

## Install and dependencies

From a complete orchflows-light checkout, run `python scripts/orchflows.py setup --example short-video` (Python 3.11+). Setup preserves existing libraries and installs no media dependencies. Core `docs/hosts.md` covers host registration and refresh; `docs/home.md` covers home updates.

Invoke `short-video:short-video` with the subject, audience, intent, placements, constraints and output location.

Requires orchflows-light 0.6.0+, native child delegation, an authoring/export toolchain and access to exports. Full audiovisual review requires motion viewing and listening; limited tools produce partial review. [Remotion](references/remotion.md) is optional. Generated projects carry their own dependencies in the caller's workspace.
