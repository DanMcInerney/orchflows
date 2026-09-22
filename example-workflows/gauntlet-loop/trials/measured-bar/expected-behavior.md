The lead uses the named reference implementation and corpus as the bar, splits the work into separately measurable pieces such as quoting, line endings and throughput, and adds no round limit of its own.

Critics run the correctness and timing comparisons themselves on the frozen candidate, under matched conditions, rather than reading builder-reported numbers. Blind labels are unnecessary for measurements, and the critic says so. Matching the reference's correctness reaches the bar; it does not loop forever on a tie. A piece that falls short returns its largest measured gap; one that reaches the bar is confirmed by a fresh critic's matched re-run, not a reversed-order judgment.

When stopped, the run returns promptly with the parser, per-piece verdicts and remaining gaps, rounds, stop reason and a record that lets a later session resume without redoing judged rounds.
