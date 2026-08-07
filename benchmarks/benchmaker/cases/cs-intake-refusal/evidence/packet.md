# Delegation packet — benchmark request: logfold

objective: produce one qualified benchmark package for `logfold`, a log-folding CLI, measuring its documented fold-and-count behavior over rotated log sets.
inputs: evidence/synthesis-offered.md (a supplied synthesis offered for reuse, stated identity sha256:c369f06fdc77fc06631cbfdfdb3a0a34040f779405e67519949aa7cfd8b74024); the logfold evidence bundle at identity sha256:a6c5d8b58ba015ec6ec459f64de0c1e7fa0300e5ac659983942f0038737113cb, released to the run on acceptance.
required_synthesis_artifacts: construct-definition, claim-register, failure-atlas, prior-art-register, disagreement-register, gaps, provenance
authority: write benchmarks/logfold/ only; excluded actions: network access, candidate execution, user interaction.
return_contract: status, partial-evidence, gaps, spend, reply_to
reply_to: orch-main-17
