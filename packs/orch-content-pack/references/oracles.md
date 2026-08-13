# Content oracle policy

| criterion kind | oracle | oracle_class | provenance |
| --- | --- | --- | --- |
| length/structure shape | word count and section presence checks | deterministic | authored-here |
| citations present and resolving | citation check over the assembled document | evidence | authored-here |
| voice | the lens's voice rubric against the spec's voice contract, via `orch-verify` | judged | authored-here |
| argument/structure quality | the lens's structure rubric, via `orch-verify` | judged | authored-here |
| claim support | each claim traced to the spec's evidence | evidence | authored-here |

Green is measured at the assembled document for the deterministic and
evidence rows and at the gate for the judged rows, compared against the
spec's own targets — its word and section counts, its evidence set, its
voice contract — and never against a prior revision, since the document
is the subject.
