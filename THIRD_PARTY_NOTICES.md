# Third-party notices

## Distributed dependency inventory

The following third-party packages are part of an installed orchflows
distribution. Versions are exact; Python identities come from
`requirements-runtime.txt`, and browser identities come from the production
dependency closure in `pnpm-lock.yaml`.

Artifact abbreviations used below are:

- **P** — the package's module and distribution metadata beneath the private
  runtime's `~/.orchflows/runtime/{Lib,lib}/site-packages/` directory.
- **B** — the immutable browser application bundle
  `web/dist/assets/index-*.js` installed by orchflows.
- **E** — the immutable ELK worker bundles
  `web/dist/assets/elk.worker-*.js` and
  `web/dist/assets/elk-worker.min-*.js` installed by orchflows.

### Python runtime

| Package | Version | Source | License | Artifact |
| --- | --- | --- | --- | --- |
| anyio | 4.12.1 | [PyPI](https://pypi.org/project/anyio/4.12.1/) | MIT | P: `anyio/` |
| click | 8.1.8 | [PyPI](https://pypi.org/project/click/8.1.8/) | BSD-3-Clause | P: `click/` |
| colorama | 0.4.6 | [PyPI](https://pypi.org/project/colorama/0.4.6/) | BSD-3-Clause | P: `colorama/` |
| exceptiongroup | 1.3.1 | [PyPI](https://pypi.org/project/exceptiongroup/1.3.1/) | MIT | P: `exceptiongroup/` |
| h11 | 0.16.0 | [PyPI](https://pypi.org/project/h11/0.16.0/) | MIT | P: `h11/` |
| idna | 3.19 | [PyPI](https://pypi.org/project/idna/3.19/) | BSD-3-Clause | P: `idna/` |
| starlette | 0.49.3 | [PyPI](https://pypi.org/project/starlette/0.49.3/) | BSD-3-Clause | P: `starlette/` |
| typing-extensions | 4.16.0 | [PyPI](https://pypi.org/project/typing-extensions/4.16.0/) | PSF-2.0 | P: `typing_extensions.py` |
| uvicorn | 0.34.3 | [PyPI](https://pypi.org/project/uvicorn/0.34.3/) | BSD-3-Clause | P: `uvicorn/` |

### Browser runtime

| Package | Version | Source | License | Artifact |
| --- | --- | --- | --- | --- |
| @floating-ui/core | 1.8.0 | [npm](https://www.npmjs.com/package/@floating-ui/core/v/1.8.0) | MIT | B |
| @floating-ui/dom | 1.8.0 | [npm](https://www.npmjs.com/package/@floating-ui/dom/v/1.8.0) | MIT | B |
| @floating-ui/react-dom | 2.1.9 | [npm](https://www.npmjs.com/package/@floating-ui/react-dom/v/2.1.9) | MIT | B |
| @floating-ui/utils | 0.2.12 | [npm](https://www.npmjs.com/package/@floating-ui/utils/v/0.2.12) | MIT | B |
| @radix-ui/primitive | 1.1.7 | [npm](https://www.npmjs.com/package/@radix-ui/primitive/v/1.1.7) | MIT | B |
| @radix-ui/react-arrow | 1.1.15 | [npm](https://www.npmjs.com/package/@radix-ui/react-arrow/v/1.1.15) | MIT | B |
| @radix-ui/react-collection | 1.1.15 | [npm](https://www.npmjs.com/package/@radix-ui/react-collection/v/1.1.15) | MIT | B |
| @radix-ui/react-compose-refs | 1.1.5 | [npm](https://www.npmjs.com/package/@radix-ui/react-compose-refs/v/1.1.5) | MIT | B |
| @radix-ui/react-context | 1.2.2 | [npm](https://www.npmjs.com/package/@radix-ui/react-context/v/1.2.2) | MIT | B |
| @radix-ui/react-direction | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-direction/v/1.1.4) | MIT | B |
| @radix-ui/react-dismissable-layer | 1.1.19 | [npm](https://www.npmjs.com/package/@radix-ui/react-dismissable-layer/v/1.1.19) | MIT | B |
| @radix-ui/react-id | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-id/v/1.1.4) | MIT | B |
| @radix-ui/react-popper | 1.3.7 | [npm](https://www.npmjs.com/package/@radix-ui/react-popper/v/1.3.7) | MIT | B |
| @radix-ui/react-portal | 1.1.17 | [npm](https://www.npmjs.com/package/@radix-ui/react-portal/v/1.1.17) | MIT | B |
| @radix-ui/react-presence | 1.1.10 | [npm](https://www.npmjs.com/package/@radix-ui/react-presence/v/1.1.10) | MIT | B |
| @radix-ui/react-primitive | 2.1.10 | [npm](https://www.npmjs.com/package/@radix-ui/react-primitive/v/2.1.10) | MIT | B |
| @radix-ui/react-roving-focus | 1.1.19 | [npm](https://www.npmjs.com/package/@radix-ui/react-roving-focus/v/1.1.19) | MIT | B |
| @radix-ui/react-slot | 1.3.3 | [npm](https://www.npmjs.com/package/@radix-ui/react-slot/v/1.3.3) | MIT | B |
| @radix-ui/react-tabs | 1.1.21 | [npm](https://www.npmjs.com/package/@radix-ui/react-tabs/v/1.1.21) | MIT | B |
| @radix-ui/react-tooltip | 1.2.16 | [npm](https://www.npmjs.com/package/@radix-ui/react-tooltip/v/1.2.16) | MIT | B |
| @radix-ui/react-use-callback-ref | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-callback-ref/v/1.1.4) | MIT | B |
| @radix-ui/react-use-controllable-state | 1.2.6 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-controllable-state/v/1.2.6) | MIT | B |
| @radix-ui/react-use-effect-event | 0.0.5 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-effect-event/v/0.0.5) | MIT | B |
| @radix-ui/react-use-is-hydrated | 0.1.3 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-is-hydrated/v/0.1.3) | MIT | B |
| @radix-ui/react-use-layout-effect | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-layout-effect/v/1.1.4) | MIT | B |
| @radix-ui/react-use-rect | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-rect/v/1.1.4) | MIT | B |
| @radix-ui/react-use-size | 1.1.4 | [npm](https://www.npmjs.com/package/@radix-ui/react-use-size/v/1.1.4) | MIT | B |
| @radix-ui/react-visually-hidden | 1.2.11 | [npm](https://www.npmjs.com/package/@radix-ui/react-visually-hidden/v/1.2.11) | MIT | B |
| @radix-ui/rect | 1.1.3 | [npm](https://www.npmjs.com/package/@radix-ui/rect/v/1.1.3) | MIT | B |
| @xyflow/react | 12.11.3 | [npm](https://www.npmjs.com/package/@xyflow/react/v/12.11.3) | MIT | B |
| @xyflow/system | 0.0.80 | [npm](https://www.npmjs.com/package/@xyflow/system/v/0.0.80) | MIT | B |
| classcat | 5.0.5 | [npm](https://www.npmjs.com/package/classcat/v/5.0.5) | MIT | B |
| d3-color | 3.1.0 | [npm](https://www.npmjs.com/package/d3-color/v/3.1.0) | ISC | B |
| d3-dispatch | 3.0.1 | [npm](https://www.npmjs.com/package/d3-dispatch/v/3.0.1) | ISC | B |
| d3-drag | 3.0.0 | [npm](https://www.npmjs.com/package/d3-drag/v/3.0.0) | ISC | B |
| d3-ease | 3.0.1 | [npm](https://www.npmjs.com/package/d3-ease/v/3.0.1) | ISC | B |
| d3-interpolate | 3.0.1 | [npm](https://www.npmjs.com/package/d3-interpolate/v/3.0.1) | ISC | B |
| d3-selection | 3.0.0 | [npm](https://www.npmjs.com/package/d3-selection/v/3.0.0) | ISC | B |
| d3-timer | 3.0.1 | [npm](https://www.npmjs.com/package/d3-timer/v/3.0.1) | ISC | B |
| d3-transition | 3.0.1 | [npm](https://www.npmjs.com/package/d3-transition/v/3.0.1) | ISC | B |
| d3-zoom | 3.0.0 | [npm](https://www.npmjs.com/package/d3-zoom/v/3.0.0) | ISC | B |
| elkjs | 0.12.0 | [npm](https://www.npmjs.com/package/elkjs/v/0.12.0) | **EPL-2.0 (selected option)** | E |
| lucide-react | 1.32.0 | [npm](https://www.npmjs.com/package/lucide-react/v/1.32.0) | ISC | B |
| react | 19.2.8 | [npm](https://www.npmjs.com/package/react/v/19.2.8) | MIT | B |
| react-dom | 19.2.8 | [npm](https://www.npmjs.com/package/react-dom/v/19.2.8) | MIT | B |
| scheduler | 0.27.0 | [npm](https://www.npmjs.com/package/scheduler/v/0.27.0) | MIT | B |
| use-sync-external-store | 1.6.0 | [npm](https://www.npmjs.com/package/use-sync-external-store/v/1.6.0) | MIT | B |
| zustand | 4.5.7 | [npm](https://www.npmjs.com/package/zustand/v/4.5.7) | MIT | B |

The `@types/d3-*`, `@types/react`, and `@types/react-dom` packages present in
the development lock contain declarations only. TypeScript erases those
declarations, and no code from them is present in an installed browser
artifact. Likewise, the packages under `devDependencies` are build and test
tools and are not installed or distributed to an orchflows user.

The Eclipse Layout Kernel JavaScript distribution offers a choice of license.
Orchflows elects the **Eclipse Public License 2.0 (EPL-2.0)** option for
`elkjs==0.12.0`.

## Adapted engineering material

Portions of the initial engineering skill semantics and reference material are
adapted from [`mattpocock/skills`](https://github.com/mattpocock/skills) at
commit `d574778f94cf620fcc8ce741584093bc650a61d3`.

```text
MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
