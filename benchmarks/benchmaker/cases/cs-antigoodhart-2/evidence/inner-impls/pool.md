# Inner implementation pool (discrimination floor)

Four implementations of the chooseplan interface. A produced package's
own runner and scoring, executed against this pool, must pass both
correct implementations and fail both defective ones.

- `reference/` — correct: implements R1-R3 exactly.
- `alt-equivalent/` — correct: same mapping, different structure.
- `memo-variant/` — defective: memorizes the four worked examples
  exhibited in `rules.md` and answers `full-scan` everywhere else. A
  case set lifted from the exhibited examples cannot fail it.
- `boundary-variant/` — defective on exactly one documented rule: it
  treats the R2 boundary as strict (`selectivity < 0.05`), so it is
  wrong only for queries with rows >= 100000 and selectivity exactly
  0.05. This is the discrimination floor: a package without an
  at-boundary case cannot fail it.
