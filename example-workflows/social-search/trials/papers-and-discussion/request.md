# Papers, blogs and discussion trial

Run a stable candidate from an unrelated project with installed libraries or explicitly resolved candidate roots. Give the workflow runner this request and a task output directory; keep [expected behavior](expected-behavior.md) separate from its input.

> [invoke `social-search:social-search`] Assess which recent quantum-computing advances have useful evidence behind them and how people are discussing them. Include original research papers, author or lab blog posts, and public Hacker News or Reddit discussion published from 2026-08-13 through 2026-09-12. Keep older context separate. Return a concise cited report with at most four ranked evidence items, explaining evidence strength separately from measured reach and stating coverage limits.
>
> Use public read-only tools. Allow twelve search/read targets total; each target in a batch counts separately. Return within six minutes of workflow start, including evidence handoffs and final review. A supported partial result is acceptable. Save the evidence handoffs and final report in the supplied output directory.

Replace the explicit dates when testing another period. These bounds belong to this request, not the workflow. They count native targets, not underlying network attempts, and do not promise cancellation of an admitted read.
