# Request

[invoke `benchmaker:benchmaker`] Build a development suite for the supplied coding workflow on a supplied fixed snapshot of a real project. Tasks should be change requests a maintainer would spend hours on, across at least three behavior families, and must preserve existing behavior. Compare the workflow with the same model working alone. Allow at most 40 executions with separate working copies, twenty minutes each. Grade delivered behavior with local checks; do not publish, deploy or install additional services. Keep output in this workspace.

Trial setup: provide a clean project snapshot as a Git repository with history, public requirements, installed runtime and the actual coding workflow invocation. Record content identity. The workflow must receive a real change request rather than instructions to emit a canned patch.
