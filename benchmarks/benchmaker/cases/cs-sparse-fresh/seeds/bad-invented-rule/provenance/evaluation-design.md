# Evaluation design excerpt — QML-lite linter benchmark

Frozen before construction; candidate-blind.

- Outcome: the finding set the linter emits for one config text.
- License boundary: only the four behaviors `evidence/spec.md`
  documents are cased — key syntax, integer scalar, comment form,
  section header — each criterion citing the documenting line id.
- Gap law: every construct the samples exhibit without documentation
  is declared in the package gap register and left uncased; the
  benchmark asserts no semantics for it.
- Selection rationale: valid and violating inputs per documented
  behavior, including the full documented key range, never only the
  key names the samples happen to exhibit.
