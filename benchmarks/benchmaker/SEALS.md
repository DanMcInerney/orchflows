# Case-set seals

One entry per seal, newest first. The recipe is owned by
`tools/seal_set.py`: the sealed scope is every file under
`benchmarks/benchmaker/` except `benchmark.lock`, `SEALS.md`, and the
`FINDINGS-*.md` campaign histories; `benchmark.lock` carries one
`<sha256>  <posix-path>` line per file, in byte order of the posix
paths, over exact working-tree bytes (`.gitattributes` pins LF); the
set digest is the sha256 of `benchmark.lock`'s exact bytes. Verify any entry with:

    uv run --no-project python benchmarks/benchmaker/tools/seal_set.py --verify

## 2026-08-07 — thirteen-case set

    sha256:ff7d9aada981e76248e96d6284ab7b5e09551e19d6e18eea7a968a536de675d0

179 files. Adds the `ranking` → `candidate-ranking` matrix row
(FINDINGS-EVOLVE next-step 4) and the seal tooling itself; first
entry sealed under this recipe and the first to carry a durable
`benchmark.lock`.

Supersedes `sha256:fb7cd69d…f42b9d15` — the B(0) seal over the
twelve-case set @ 966d8de (see FINDINGS-EVOLVE.md). That identity
stopped describing the tree when the fourteen-key schema supersession
changed the case bytes; no campaign may cite it against this tree. A
campaign consuming the set cites the digest above; any later change
to a sealed byte mints a successor entry here.
