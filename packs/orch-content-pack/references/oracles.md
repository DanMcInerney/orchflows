# Content oracle policy

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| length/structure shape | word count and section presence checks | deterministic | authored-here |
| citations present and resolving | citation check over the assembled document | evidence | authored-here |
| voice | the lens's voice rubric against the spec's voice contract, via `orch-verify` | judged | authored-here, gate re-verified |
| argument/structure quality | the lens's structure rubric, via `orch-verify` | judged | authored-here, gate re-verified |
| claim support | each claim traced to the spec's evidence | evidence | authored-here |

Green means: deterministic and evidence rows pass at the assembled
document; judged rows are settled at the gate, fresh from the spec.
