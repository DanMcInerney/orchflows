# Synthesis — logfold (supplied for reuse)

identity: sha256:c369f06fdc77fc06631cbfdfdb3a0a34040f779405e67519949aa7cfd8b74024

## Construct definition

logfold folds runs of adjacent duplicate log lines into one line with
a trailing count marker. The capability measured is fold-and-count
correctness over rotated log sets: folding, count accuracy, and
byte-exact passthrough of non-duplicate lines.

## Claim register

- CL1: adjacent duplicate lines fold into one line carrying a count
  marker (source: README section 2; falsifier: a duplicate pair
  emitted unfolded).
- CL2: a rotation boundary does not split a fold (source: demo
  transcript; falsifier: the count resetting at a file boundary).
- CL3: non-duplicate lines pass through byte-exact (source: README
  section 2; falsifier: any byte drift on a unique line).
- CL4: counts render in decimal with no width limit (source: README
  section 4; falsifier: a truncated count past three digits).

## Failure atlas

- boundary-shift at rotation seams (fold split or merged across the
  seam);
- value-truncation of counts past three digits;
- state-omission when the fold buffer is dropped at end of input.

## Prior-art register

- uniq -c: adapt — fold semantics agree within one file, differ at
  rotation boundaries;
- logmerge-bench (2019): ignore — measures merge ordering, not
  folding.

## Disagreement register

None recorded; the surveyed sources do not contradict each other on
any cased behavior.

## Gaps

- No demand or failure-record mining was performed; the demand record
  was unavailable offline.

## Sourcing mode

Authored: cases are to be authored from the README semantics and the
demo transcript.
