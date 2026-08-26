# Research slicing: evidence lanes plus terminal synthesis

Cut the question into lanes that are independently answerable and
jointly cover it — by sub-question, by source modality, or by
competing hypothesis.

- One ticket per lane, carrying its bounded question, its fixed
  evidence sources and slice of the source policy, its lane store as
  write scope, and a bound in sources or tool calls.
- A lane item adds the modality or hypothesis it owns.
- The terminal item is the synthesis over every lane's evidence
  packet, whose claims it weighs for independence.
- Lanes are blind to each other — every lane ticket carries
  `excluded_actions`: reading sibling lane stores.
