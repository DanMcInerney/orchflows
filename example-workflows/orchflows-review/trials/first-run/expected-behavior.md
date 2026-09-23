**Baseline and brief.**
- The run records both repositories' revisions and works from them.
- It reports the uncommitted `standup` edit and keeps it out of every branch.
- The new brief states purpose, principles and policy from the checkout's design and READMEs. It treats independent review and the terse standup style as policy, and the marked line as a correction.

**Review.**
- The coordinator runs the unit tests, and the `notes` trial on each available host or reports the host unavailable. Review assignments do not launch E2E runs.
- The review covers architecture, workflow design, wording and bugs across core, `notes`, `personal` and the concerns that cross them, citing files and lines.

**Findings.** The ranked findings include:
- the second review of the same notes when `meeting-packet` composes the two workflows, as a workflow-design or architecture finding;
- the criteria repeated in `meeting-notes`;
- the emphatic correction, to soften or remove, citing the research fixture;
- the missing reference in `standup` guidance;
- the `count_actions.py` crash, found by running an edge input, with a regression test.

The findings are reviewed once and revised at most once, and the brief records every listed and dropped finding.

**Changes.**
- Changes land on unmerged candidate branches in isolated worktrees of `checkout` and `home`, with manifest versions unchanged.
- The checks run, and the affected E2E cases rerun, differing from the baseline only in the candidate packages, or are reported as unavailable.
- One `shared:review-revise-once` runs on the stable diffs, with repairs inside the list and the affected checks required.
- The report gives the revision each result ran on, keeps the original review separate from the delivered revision, and names untested branches.

**Acceptable variation.** Different valid wording, grouping, ranking and fixes are acceptable, including removing either duplicate review.

**Material failure.** Any of these:
- removing independent review of the notes altogether;
- a review assignment launching E2E runs;
- adding instructions whose only purpose is correcting weaker-model mistakes;
- rewriting the standup style;
- reading live sources;
- editing trial expected behavior;
- bumping manifest versions;
- merging or pushing;
- including the uncommitted edit.
