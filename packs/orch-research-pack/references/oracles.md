# Research oracle policy

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| citations resolve | each cited source fetched or located | evidence | authored-here |
| sources support claims | sampled claim-to-source reads | evidence | authored-here |
| coverage | every acceptance sub-question answered or an explicit gap | evidence | authored-here |
| contradiction handling | the disagreement register faithfully carries lane disagreements, judged from the lane packets | judged | authored-here |
| independence | converging claims trace to sources with no shared upstream, per the claim-to-source trace | evidence | authored-here |
| rigor | the lens's rigor rubric against the spec's rigor bar, via `orch-verify` | judged | authored-here |

Green is measured at the synthesized result for the evidence rows and
at the gate for the two judged rows — contradiction handling and rigor
— which no evidence row's passing carries. Evidence rows are compared
against the sources they cite, the judged rows against the lane packets
and the spec's rigor bar. No deviation from
[verdict.md](../../../contracts/verdict.md)'s class policy: follow it
for how each class decides.
