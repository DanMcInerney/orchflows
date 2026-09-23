# Expected behavior

- **Real modality inspection.** An example is inspected in its actual rendered modality before criteria are finalized. The auditor and reviewers read actual rendered slides.
- **Deterministic where possible.** Factual and format constraints are checked deterministically against source assets where possible, separately from anchored readability and audience judgments. Alternative layouts can pass.
- **Adversary fails.** Attempts such as padding slides with source text, fabricating figures or satisfying format checks with empty slides fail.
- **Artifact evidence.** Produced decks and visual evidence are retained. Parsed text or file existence alone does not establish artifact quality.
- **Provisional judging.** Missing rendering or judge access leaves affected metrics provisional, without silent string-match substitutions. Uncalibrated judging stays provisional.
- **Comparison set.** The workflow is compared with a simple baseline at matched budget, or the baseline's absence within twelve executions is explained.
- **Honest delivery.** Real native execution, raw criterion evidence, the rejection log, elapsed time and cost, and the twelve-execution limit are reported.
