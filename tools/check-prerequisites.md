# Check prerequisites

Before running the required checks or `tools/preflight.py` in a fresh checkout,
install Node.js 24.15.0 (the CI version) and provision the workflow's locked
JavaScript dependencies from the repository root:

```sh
npm ci --prefix example-workflows/3d-browser-game --ignore-scripts --no-audit --no-fund
```

The lineage fixture creates its own temporary Git history.
Repeat the dependency install after its lockfile changes. The Python
play-evidence tests import this package; they do not require a browser download. Preflight reuses these local
dependencies and does not provision them itself.

