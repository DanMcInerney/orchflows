# Remotion, when chosen

Use the available [official Remotion skills or plugin](https://www.remotion.dev/docs/ai/skills) for creating, previewing and rendering. The official skill collection is installable with `npx skills add remotion-dev/skills`; host plugins have [their own installation instructions](https://www.remotion.dev/docs/ai/plugins). Availability must be checked in the actual host.

A local project needs a supported Node.js/npm or Bun runtime, React, compatible Remotion packages and the renderer's browser, fonts and media. Retain its lockfile and use documentation matching its installed version. The [documented CLI](https://www.remotion.dev/docs/cli/render) renders a project directly:

```text
npx remotion render <entry-point> <composition-id> <output-path>
```

Use existing native rendering facilities or this documented project toolchain; the workflow ships no substitute renderer. Keep timing driven by composition frames, centralize shared timing and make procedural variation reproducible. Preview and inspect the final encoded output separately. Remotion's [rendering documentation](https://www.remotion.dev/docs/render) describes the available routes; a Studio preview is not the delivered encode.

Remotion v4 bundles a [lightweight FFmpeg](https://www.remotion.dev/docs/ffmpeg). General inspection commands may need filters, formats or default encoders it omits. Reuse an available full build when needed, or choose supported codecs explicitly for decoding; check the operation before building verification helpers around it.

For product marketing, [source observations](marketing-reference.md) offer optional context. They establish neither required style nor measured effectiveness.
