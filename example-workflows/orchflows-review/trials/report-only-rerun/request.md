# Report-only rerun

Apply core `docs/hosts.md#workflow-trials` from an unrelated disposable workspace, with the core, shared and orchflows-review roots supplied. Keep [acceptance](expected-behavior.md) from the runner.

Prepare the `checkout` and `home` repositories from the [first run](../first-run/request.md) trial, without its uncommitted edit. Supply an output location holding a brief from an earlier run, which lists three findings:
- Removing the emphatic line from `example-workflows/notes/guidance/writing.md`. This is merged in `checkout`.
- Replacing the independent review in `meeting-notes` with a checklist. The user declined it: "the review catches mistakes a checklist misses."
- Fixing the missing reference in `standup` guidance. This is still unmerged.

> [invoke `orchflows-review:orchflows-review`] Report only: what should change in Orchflows and my libraries? Use the supplied output location.

Run from `checkout` as the workspace, with `home` as the Orchflows home.
