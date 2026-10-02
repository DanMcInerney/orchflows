# logtriage-llm reference package

A hand-built, known-good benchmark package for the `logtriage-llm` meta-task: what a careful builder delivers for "benchmark our CI-failure triage prompt", in the kit's format. The meta-verifier must score it well, and the mutants made from it must be caught. Nothing here imports `metabench`: the verifier and reference are independent of the meta checker.

```text
python generate.py --instances offline|DIR --out PACKAGE [--tasks N] [--per-repo K] [--seed S] [--split development|held-out]
```

`generate.py` writes everything except the kit (`run.py`, `benchkit/`, copied from `skills/benchmaker/scripts/`). `offline` reads the committed synthetic logs in `offline-instances/` (21 candidates, 18 admitted, 8 invented repositories, 8 languages); a directory reads LogChunks-layout material, such as the `public/` or `held-out/` folder the metabench material step writes. Every candidate goes through an admission screen (label locatable and at most five occurrences, size limits, and no trivial range earns credit: whole log, whole log minus an edge, the last 50 lines, the instruction's example); rejections are logged in the package's `rejections.jsonl`. `check_admission.py PACKAGE` grades the package's labeled outcomes through its own `run.py grade` and compares them with `admission/<task>/labels.json`.

| File | Role |
| --- | --- |
| `sources/verify.py`, `sources/solve.py` | the verifier and the reference, copied into every task; constants and the grading rule are in the verifier's docstring |
| `sources/instruction.md`, `card.json`, `suite.json`, `README.md`, `research/catalog.md` | templates the generator fills |
| `outcomes.py` | labeled outcomes and the grading rule restated over sets, so the verifier is checked against a second implementation |
| `lc.py` | LogChunks-layout reading, chunk location, family guess for unlabelled material |
| `synthesize.py`, `synth_*.py` | write `offline-instances/` (reproducible: every log is seeded by its build id) |
| `offline-instances/` | synthetic Travis logs and labels in the LogChunks layout, plus `instances.json` (family and difficulty per log); `build_split` of the logtriage domain reads it as material |

Task layout the mutants edit: `tasks/<id>/tests/expected.json` holds `spans` (1-based inclusive line ranges, every occurrence of the marked text) and `chunk`; `verify.py` reads `spans` and the line count of `environment/build.log`; `solve.py` writes `spans[0]` and a summary built from the delivered log. `.gitignore` re-includes `*.log` and `.gitattributes` keeps log bytes (CRLF, lone CR, ESC) intact under `core.autocrlf`.
