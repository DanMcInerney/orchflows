# Context-packet design

The packet is the only thing an iteration receives besides the frozen
goal and worklog. Design it once, before iteration 1, for the executor
the loop freezes.

- Carry identities, verdicts, and decisions — never transcript prose.
- Include: the frozen goal and done-check verbatim; the current result
  identity; the open item; the failed-approaches digest; remaining
  budget; the done-check's latest findings or score card.
- Exclude: anything re-derivable from the workspace at iteration start,
  and anything only one past iteration cared about.
- Size test: a packet that grows with iteration count is wrong — it must
  converge to the state that matters, not accrete history.
- The packet's fields are a return contract: an iteration that cannot
  fill a field reports it, never invents it.
