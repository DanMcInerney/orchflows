# Planted defect: the gate checks the pipeline, not its output

The done check reads "every step returned status complete and reported
no blocker". Both steps are bound by invariants, the chain resolves, the
edge carries the artifact `collect` produces — the file is otherwise the
reference. The gate over the whole has been replaced by a restatement of
what the steps already reported.

A benchmark for this target must catch it, because this is the failure
that survives every structural check and still leaves the workflow
ungated. `contracts/composition.md` states the reason directly: a chain
of individually gated steps has no gate over the whole, and `done_check`
is that gate. A done check that reports step status adds nothing the
step results did not already carry, so a run where `reduce` emitted a
digest line no record supports still ends `complete`.

Catching it means deciding whether the done check names something the
pipeline produced and states a predicate over it. That is a design
decision the benchmark must make before it can be built, and it is
harder than it looks: the defective text is a well-formed English
sentence about the workflow, in the right field, and it passes any
check for the field's presence or non-emptiness.
