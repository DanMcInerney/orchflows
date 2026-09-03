# The toolchain this sheet fixes, and where each part comes from

## What the reference workspace pins

`C:\Users\danhm\tools\vampire-fps\package.json`, read 2026-09-03:
`"type": "module"`; dependency `three` at exactly `0.185.1`; devDependencies
`vite` at `8.2.2` and `playwright` at `1.62.1`; scripts `dev` (`vite`),
`build` (`vite build`), `preview`. Its README's "Run it" names Node 24 and a
committed lockfile install (`npm ci`), and `node_modules/` is not committed.
Every version is exact; none is a range.

## The one deviation this sheet makes on purpose

The reference workspace uses npm and carries `package-lock.json`. This sheet
names **pnpm** and `pnpm-lock.yaml` instead, because the workflow that stamps
it declares pnpm in its `tools.txt` and one toolchain has to be named once.
The substance the reference workspace proves — an exactly pinned dependency
set, a committed lockfile, a lockfile install, `node_modules/` ignored — is
what carries over; which of the two lockfile formats holds it does not change
any of it. Recorded here because a sheet clause with no source behind it is
an opinion wearing a pin.

## Node's floor

`engines.node` at `>=20`: 20 is the oldest release line still receiving
security fixes, and the workspace this sheet was written from runs Node 24
(`node --version` on the authoring host, 2026-09-03: `v24.15.0`), so the
floor is below the measured host rather than equal to it.

## Where the artifact's dependencies live

`docs/custom-workflow-authoring.md` §Dependencies, in the library this sheet
is stamped by: "A game's three.js, a site's build tool and their lockfiles
belong to the workspace's own manifest, installed by the child in its
worktree as part of making the artifact and committed with it. Orchflows
never owns them."
