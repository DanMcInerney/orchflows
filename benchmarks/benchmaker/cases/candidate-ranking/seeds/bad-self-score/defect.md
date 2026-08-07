# bad-self-score

When a record carries an integer `self_score`, this seed substitutes
it for the computed aggregate. The contract says keys beyond `candidate`
and `results` are ignored precisely because they are the candidate's
own voice: a claimed score is self-declared evidence, and the
protocol's qualification law is that self-declared verdicts never
qualify anything. This ranker lets any candidate that writes a large
enough number into its own record buy rank 1.

The deviation is reachable only through a case whose records include
the extra key: a candidate with `"self_score": 999` and a middling
`results` table must still rank by its computed score. On records
that carry only `candidate` and `results` — every honest harness's
output — the seed is byte-identical to the reference, so a benchmark
built solely from well-behaved fixtures reports it correct while it
remains one adversarial record away from a bought ranking.

deviation: self-reported-score-trusted
