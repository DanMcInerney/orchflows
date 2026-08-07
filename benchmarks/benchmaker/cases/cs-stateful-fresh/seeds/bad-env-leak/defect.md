# bad-env-leak

The harness exports `MIGRATION_SAFE=1` into the inner process
environment alongside the platform allowlist. The spec's
no-env-dependence law makes any such export unlawful: state must
live in the journal file and nowhere else. The export opens an
escape hatch — an implementation that consults the variable can
detect "benchmark mode" and behave idempotently while remaining
broken in production environments where the variable is absent. The
re-migrating inner variant does exactly that: under this package's
leaked guard it hides its second-run corruption and passes, so the
package can no longer discriminate the defect class the case exists
for.

deviation: guard-insertion @ env-var-leak locus (harness exports MIGRATION_SAFE=1, hiding the state defect)
