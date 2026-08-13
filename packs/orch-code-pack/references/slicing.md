# Code slicing: tracer-bullet tickets

Cut the spec into tracer tickets: each crosses the system end to end
at one thin point, proving the seams early, then widens — never
layer-by-layer slices that integrate only at the end; the first
frontier carries the riskiest seam's tracer.

- Each ticket: one observable behavior, provable by runnable checks from
  the spec's acceptance; a write scope overlapping only siblings it is
  dependency-ordered with and sufficient for its own completion test;
  dependency edges only where one ticket's seam is another's input.
- Item extensions beyond the core: the runnable check commands verbatim;
  the standards owner pointer.
- No terminal assembly item: merged, green revisions are the assembled
  deliverable.
- A criterion needing simultaneous changes across most of the surface is
  a decision gap (the slicing cannot isolate it), not one giant ticket
  (rules/topology.md §3).
