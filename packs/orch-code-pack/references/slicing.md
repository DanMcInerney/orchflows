# Code slicing: tracer-bullet tickets

Cut the spec into tracer tickets: each crosses the system end to end
at one thin point, proving the seams early, then widens; the first
frontier carries the riskiest seam's tracer.

- Each ticket: one observable behavior, provable by runnable checks from
  the spec's acceptance; dependency edges only where one ticket's seam
  is another's input.
- Also verbatim in each item: the runnable check commands; the
  standards owner pointer.
