# Code slicing: acceptance-first tickets

Every seam the spec's acceptance already checks is its own item on the
first frontier. Cut a tracer — one thin end-to-end crossing, taken
first and widened after — only for the riskiest seam the spec leaves
unproven.

- Each ticket: one observable behavior, provable by runnable checks from
  the spec's acceptance; dependency edges only where one ticket's seam
  is another's input.
- Also verbatim in each item: the runnable check commands; the
  standards owner pointer.
