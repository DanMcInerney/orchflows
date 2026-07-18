# Research slicing: evidence lanes plus terminal synthesis

Cut the question into lanes that are independently answerable and
jointly cover it — by sub-question, by source modality, or by
competing hypothesis; state which cut you used and why it covers.

- Each ticket: one bounded question; its fixed evidence sources and
  slice of the source policy; a lane store as write scope; a bound in
  sources or tool calls.
- Item extensions beyond the core: the modality or hypothesis the lane
  owns; what would make the lane's answer decisive; the pack's craft
  reference by path. Every item carries its lane store path; the
  executor's return files the store artifacts' identities into the
  ticket's `## Result` per the filing law.
- Terminal assembly item: `orch-synthesize`, combining the evidence
  packets from every lane, completion test carrying the spec's
  coverage and rigor criteria.
- Lanes are blind to each other — every lane ticket carries
  `excluded_actions`: reading sibling lane stores; convergence found
  at synthesis is evidence, convergence built in by shared drafting is
  contamination.
