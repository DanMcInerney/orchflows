---
name: threejs
description: Stamp when the artifact is a browser game drawn with three.js and shipped as a static site.
packs: [orch-code-pack, orch-design-pack]
---

# threejs

## Vocabulary

- **measurement seam** — one object the running page publishes on `window`
  that a probe reads to learn what the simulation did.
- **cell** — one measured environment: OS, CPU, GPU, browser build, pinned
  versions. A figure without its cell transfers nowhere.

## Craft

- **The toolchain is fixed, not chosen per repository.** pnpm with
  `pnpm-lock.yaml` committed beside `package.json`; `engines.node` set to
  `>=20`; vite as dev server and bundler; `node_modules/` in `.gitignore`
  and never committed. Every dependency is pinned to an exact version, the
  way the reference workspace pins `three` and `vite`
  ([references/toolchain.md](references/toolchain.md)).
- **The deliverable is a directory, not a server.** `vite build` writes a
  `dist/` any static file host serves at any path, and the page makes no
  network request after load. Anything the game needs is in the bundle
  ([references/vampire-fps.md](references/vampire-fps.md)).
- **WebGL2 is the default renderer; WebGPU is a measured exception.** On
  the one measured cell every three.js WebGPU arm was slower than its
  WebGL2 sibling — 3.664 ms against 0.788 ms p95 at n=4000 instanced, and
  35.263 against 3.709 unbatched — and cost 74–108 KB more gzipped
  ([references/bakeoff.md](references/bakeoff.md)). Choosing WebGPU here
  needs a figure from this artifact's own cell, not a preference.
- **Repeated entities are drawn instanced.** Unbatched three.js issues one
  draw call per entity and doubles its p95 by n=1000 on WebGL2, which is
  under this genre's entity count; instanced, the same family sits an
  order of magnitude inside the same budget
  ([references/bakeoff.md](references/bakeoff.md)). Keep the frame's draw
  calls a bounded number the probe asserts.
- **The page publishes one measurement seam.** A single object on `window`
  — ready flag, tick, player position, phase, draw calls — plus a way to
  sample the drawn frame. A probe that reads only the DOM passes while the
  renderer draws nothing, which is the bake-off's own lesson
  ([references/vampire-fps.md](references/vampire-fps.md)).
- **Pointer lock is requested, never assumed.** The browser may refuse it.
  The page says so in itself and keeps playing on the keyboard; a build
  that needs relative mouse-look to start is broken on a machine that
  refuses ([references/vampire-fps.md](references/vampire-fps.md)).
- **The artifact owns its dependencies.** They live in this workspace's
  `package.json` and lockfile, committed with the code. No orchflows ring
  item declares them ([references/toolchain.md](references/toolchain.md)).

## Lens

### git

- Toolchain: `package.json` has `engines.node` `>=20` and vite; a
  `pnpm-lock.yaml` is committed; `.gitignore` names `node_modules/`; no
  dependency range is loose. Read the three files.
- Static delivery: `pnpm build` exits 0 and writes `dist/`; the probe loads
  the built directory from a file server rather than the dev server, and
  records zero requests after load.
- Renderer: the code constructs a WebGL2 renderer, or the revision carries
  a figure from its own cell for the WebGPU one. Read the constructor and
  the report.
- Instancing: the probe's recorded draw-call count is bounded and the bound
  is asserted, not printed. A count that grows with live entities is a
  finding.
- Seam: the probe reads a `window` object for tick, position and phase, and
  samples lit pixels of the drawn frame. A probe that asserts only on the
  DOM is a finding whatever it passes.
- Input: pressing the movement key through the browser changes the seam's
  reported position; a refused pointer lock leaves a message in the page
  and the run still playable.
- Console: the probe records zero page errors and zero console errors over
  the whole run, asserted rather than logged.
