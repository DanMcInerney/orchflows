# chooseplan benchmark package — interchange formats

Normative formats for a produced benchmark package. A package is a
directory; paths are relative to its root, forward slashes.

## Manifest

`manifest.json` is a JSON object with exactly these ten fields:

    evaluation_design, runnable_cases, runner, scoring, provenance,
    qualification, expected_cost, gaps, protected_evidence, attack_audit

`attack_audit` records `checklist_identity`, `outcomes` per attack
class, and `unrepaired` — an explicit list in which every entry names
the `attack` that works.

These are recorded once qualification closes and are not re-derivable
afterwards, which is why the manifest carries them. Other
post-qualification fields may be present and are not read here.

The six component fields — `evaluation_design`, `runnable_cases`,
`runner`, `scoring`, `provenance`, `qualification` — are component
references:

```json
{"locator": "cases/cases.json"}
```

`locator` is a forward-slash path resolving inside the package root.
`gaps` is an explicit list (empty allowed).

## Runner invocation

The `runner` component is executed as one positional argument — the
directory of the implementation under test — with no flags and no
other arguments:

    python <runner> <impl-dir>

The working directory at invocation is a scratch directory outside the
package, so the runner resolves its own components relative to its own
file location, never to the process working directory. Exit status is
the verdict: `0` when the implementation under test passes, non-zero
when it fails. `PYTHONDONTWRITEBYTECODE` is set in the environment.

`BENCH_PROTECTED_DIR` is absent from the environment for public
scoring and carries the protected store's root when held-back scoring
is in scope. When it is present, the runner's **last line of stdout**
is a JSON object carrying `protected_ids` — the identifiers of the
held-back cases it scored — and `failed`, the identifiers it failed.
Both keys are lists.

## Qualification component

A JSON object with `entries` and `overall`. Each entry carries
`criterion`, `verdict`, `oracle`, `oracle_class`, `evidence`, `covers`
and a boolean `required`. `verdict` is one of `PASS`, `FAIL`,
`UNVERIFIED`; a PASS entry's `evidence` is non-empty; `covers` is a
non-empty list. `overall` is an object carrying the aggregate
verdict:

```json
{"verdict": "PASS"}
```
