# Package interchange contract

The manifest and qualification shapes every consumer of a benchmark
package for this target relies on. A package that departs from any
shape below is rejected. Workflow-specific paths and command lines are
in `pipeline-spec.md` §Package interface.

## Manifest

`manifest.json` sits at the package root and carries exactly these ten
fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence, retirement_trigger

`retirement_trigger` carries the declaration only. A recorded firing
belongs in the measurement record outside the package.

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

Each of the six components — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — is a reference
object of exactly this form:

    {"locator": "<posix-relative-path>"}

Locators are forward-slash paths relative to the package root and must
resolve inside it, to a file or to a directory.

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
