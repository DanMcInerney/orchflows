The platform migration standup confirmed that the payments service is
now scheduled to move onto the v2 runtime on 2026-08-20, with Priya
named as the accountable owner for the cutover as a whole [m1-02]. The
staging soak that preceded this decision ran for a full 72 hours and
showed no regressions of any kind across that entire window [m1-03].
There remains an open risk in that the legacy cron jobs are still
writing into the old queue today [m1-04], and Jonas has taken the
action to draft the complete cron cutover plan by Friday [m1-05]. The
incident review for INC-2214 walked through the checkout latency spike
of 2026-07-29, which lasted forty-one minutes end to end [m2-01], and
traced the root cause to connection pool exhaustion that followed the
doubling of the retry budget [m2-02]. As a consequence the retry budget
reverts to 3 attempts with Wei as owner [m2-03], the paging policy gap
around the secondary on-call stays open [m2-04], and Dana re-tests the
paging rotation before the next release goes out [m2-05]. On budget,
Q3 infrastructure spend is tracking 12 percent over plan [m3-01],
driven by the duplicate observability stacks [m3-02]; the legacy
metrics stack is decommissioned by 2026-09-15 under Sam [m3-03], while
the GPU reservation renewal remains undecided for now [m3-04]. The v1
export API, which still has 9 external consumers [m4-01], sunsets on
2026-11-01 under Priya [m4-02]; notices go out in two waves [m4-03],
Wei publishes the migration guide before the first wave [m4-04], and
the proposal to shorten the window to one month was rejected [m4-05].
Finally, the third platform headcount is reallocated to the SRE
rotation under Dana [m5-02], with the contractor extension under
review for one more week [m5-03].
