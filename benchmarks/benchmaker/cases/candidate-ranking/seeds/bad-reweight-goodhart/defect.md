# bad-reweight-goodhart

After every record is loaded, this seed multiplies each case weight by
one plus that case's failure count across the candidate set — a
"rarity bonus" that looks like sharpening discrimination. The
aggregation policy is thereby re-derived from the candidates it is
about to rank: the weights file stops being the whole policy the
moment the candidate set can bend it, which is the Goodhart shape the
candidate-blind design law exists to forbid.

The defect is observable two ways. Every multi-candidate run inflates
the printed scores, and on a set where one candidate monopolizes a
rarely-passed case the order itself flips: with weights `c1=3,
c2=2, c3=2` and candidates alpha (passes only c1) versus beta and
gamma (each pass c2 and c3), fixed weights rank beta and gamma first
on 4 against alpha's 3, while the rarity bonus lifts alpha to 9
against their 8 and hands it rank 1. A benchmark that never puts two
candidates with complementary pass patterns in front of the ranker
scores this seed identical to the reference and has not tested that
aggregation is fixed before candidates are seen.

deviation: candidate-derived-reweighting
