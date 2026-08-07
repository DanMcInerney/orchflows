# changelog-generator benchmark — frozen evaluation design

Target: the changelog generator fixed by the case evidence
(`code-spec.md`, `doc-spec.md`). The target spans two domains and the
benchmark cases both: code-domain laws (parsing, input-order
preservation, exit codes, no partial output) and document-domain laws
(title, section order and heading grammar, entry form, impersonal
voice). Construction was two chained single-pack runs — a code-pack
construction of the code-domain cases and a content-pack construction
of the document-domain cases — joined by a frozen evidence identity;
the join is recorded in the provenance component's `chain`.

Boundary:

- Code domain: entry sequence equals input order per section; a
  malformed line yields exit 1 with empty stdout; LF/CRLF input
  equivalence; usage errors exit 2.
- Document domain: `# Changelog` title; `## Features`, `## Fixes`,
  `## Documentation` in fixed order, present only when non-empty;
  level-two headings only; one blank line before each heading;
  entries `- ` + capitalized subject; no generator prose; forbidden
  words `we`, `our`, `awesome`; single trailing newline.
- Discrimination requirement: an implementation correct in exactly
  one domain must fail. Both single-domain-blind variants in the
  fixed inner pool are required failures.

Runner interface (frozen): `python <runner-locator> IMPL` where IMPL
is a directory holding `changelog.py` (or a direct path to it). The
runner resolves its package root by walking up to `manifest.json`,
reads cases and scoring through the manifest locators, executes each
case in a scratch directory, and emits one JSON object on stdout:
`{"impl", "cases": [{"id", "domain", "pass", "detail"}], "pass"}`,
exit 0 on aggregate pass, 1 otherwise.

Scoring: every case is required in both domains; aggregation is
all-required-pass. Output comparison normalizes CRLF to LF
(terminator form insignificant); all other checks are exact.
