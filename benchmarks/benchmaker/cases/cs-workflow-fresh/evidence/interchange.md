# Package interchange contract

The manifest and qualification shapes every consumer of a benchmark
package for this target relies on. A package that departs from any
shape below is rejected. Workflow-specific paths and command lines are
in `pipeline-spec.md` §Package interface.

## Manifest

`manifest.json` sits at the package root and carries exactly these ten
fields — no extras, none missing:

    benchmark_identity, evaluation_design, runnable_cases, runner,
    scoring, provenance, qualification, expected_cost, gaps,
    protected_evidence

`benchmark_identity` is a `sha256:`-prefixed hex string recomputable
from the canonical payload: the manifest object minus
`benchmark_identity`, serialized as JSON with sorted keys, compact
separators `(",", ":")` and `ensure_ascii=False`, digested as UTF-8.

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"identity": "sha256:<64-hex>", "locator": "<posix-relative-path>"}

Locators are forward-slash paths relative to the package root and must
resolve inside it.

## Digest rule

A file locator's identity is sha256 over the file's bytes, recorded
with the `sha256:` prefix. A directory locator's identity is the tree
digest: sha256 over the UTF-8 encoding of
`<posix-relpath>:<file-sha256-hex>` lines — one per file under the
directory, sorted by relpath, joined with `"\n"` — with `__pycache__`
directories excluded. Tree digests carry the same `sha256:` prefix.

## Qualification record

When the `qualification` locator is a directory, the record inside it
is named `qualification.json`. It is a JSON object with:

- `entries`: non-empty list of entry objects, each carrying all of
  `criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`,
  `covers`, `required`. `verdict` is one of `PASS`, `FAIL`,
  `UNVERIFIED`; `oracle_class` is one of `deterministic`, `judged`,
  `evidence`; `required` is a boolean. A `PASS` entry's `evidence` is
  a non-empty string.
- `gaps`: an explicit list (`[]` allowed).
- `overall`: a string, one of `PASS`, `FAIL`, `UNVERIFIED`. `PASS`
  cannot coexist with a required `FAIL` entry.
