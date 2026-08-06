# What makes the chain observable

A workflow file is not executable code, so "does it work?" has to be
answered from the file's own text. The observable outcome here is a
valid artifact chain, and it is observable because every reference in
the file resolves to something the file declares:

- each edge's carried artifact resolves to the predecessor step's
  `produces`;
- each edge's endpoints resolve to declared step ids;
- each invariant's subject resolves to a declared step id, and every
  step id is some invariant's subject;
- the done check's named artifact resolves to the terminal step's
  `produces`.

A file where all four resolve describes a pipeline whose output can be
traced back through every step to the caller's input. A file where any
one dangles describes a pipeline with a gap that only shows up at run
time — the step nothing constrains, the handoff that carries an
artifact nobody made, the gate that checks nothing the pipeline built.

## Why this is the recursion dry run

Benchmarking a workflow file means benchmarking the same kind of object
BenchMaker itself is defined by: `compositions/benchmaker.md` is a
workflow file with steps, edges, invariants, and a done check. A
benchmark that can decide whether *this* toy pipeline's chain resolves
is the shape a benchmark of BenchMaker needs. The toy scale is the only
difference.

## The scoring surface

Every property above is decidable from the file's bytes: no model call,
no execution, no network. That is deliberate. A benchmark whose oracle
for "is this workflow valid?" is a judged opinion has moved a decidable
question behind a scoring opinion, and inherits the judge's variance for
nothing.
