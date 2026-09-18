# Remotion, when chosen

Use available [official skills](https://www.remotion.dev/docs/ai/skills) or [plugins](https://www.remotion.dev/docs/ai/plugins) for authoring/preview/rendering; verify host availability. The skill collection installs with `npx skills add remotion-dev/skills`.

Require supported Node.js/npm or Bun, React, compatible Remotion packages and the renderer's browser/fonts/media. Retain the lockfile and use matching documentation. The [CLI](https://www.remotion.dev/docs/cli/render) supports:

```text
npx remotion render <entry-point> <composition-id> <output-path>
```

Use native rendering facilities or this project toolchain; no renderer is bundled. Drive timing by composition frames, centralize shared timing and seed procedural variation. Inspect the final encode separately from Studio preview. [Rendering routes](https://www.remotion.dev/docs/render).

Remotion v4's [lightweight FFmpeg](https://www.remotion.dev/docs/ffmpeg) omits some filters/formats/default encoders. Verify inspection commands before building helpers; use an available full build or supported codecs when needed.

[Marketing observations](marketing-reference.md) are optional context, not required style or effectiveness evidence.
