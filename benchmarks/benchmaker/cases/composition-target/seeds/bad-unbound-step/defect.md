# Planted defect: a step no invariant binds

The `publish` step is added, produces `digest.pdf`, sits on the chain
after `reduce`, and is named by the done check. Everything about it
resolves. What it does not have is a bullet in the `Never:` block: the
file states what `collect` and `reduce` must never do, and states
nothing about the step that puts the digest in front of other people.

A benchmark for this target must catch it, because this is exactly the
admission failure `contracts/composition.md` names — "a step no
invariant binds" — and it is the one defect here that is invisible to a
reader who checks that the pipeline hangs together. The chain is fine.
The gap is that `publish` runs under no stated law, so the file cannot
say what would make its output wrong: nothing forbids it circulating a
digest whose lines were never traced, because nothing was written down.
Catching it requires the benchmark to quantify over declared steps and
ask which are bound, rather than reading the invariants block and
finding it non-empty. A benchmark that only checks presence of the block
scores this file clean.

deviation: binding-omission
