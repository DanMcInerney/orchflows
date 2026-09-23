# Expected behavior

- **Native sessions.** The workflow runs natively in separate top-level sessions under core workflow-trial rules. The coordinator launches every session and counts it against the limit.
- **Matched comparison.** The baseline is the same model with the same tools and limits. The card states what was matched (time, spend or launches) and what could not be. Quality, time and spend are reported per system, and a costlier workflow that is not better is reported as worse.
- **Tasks that could separate them.** Tasks are substantial enough that the workflow's claimed advantages, such as decomposition, independent review or parallel research, could matter. Tasks either system always solves, or neither ever solves, are anchors or rejected.
- **Outcomes, not narration.** Grading uses delivered outcomes, not the workflow's narration of its process. Process properties, such as whether independent review actually occurred, are graded from native traces only when the claim is about them.
- **Honest scope.** Admission evidence, rejection log and paired per-task results are reported. With few sessions the result is a draft or a narrow development claim, and the card says so.
