# First run

Apply core `docs/hosts.md#workflow-trials` from an unrelated disposable workspace, with the core, shared and orchflows-review roots supplied. Keep [acceptance](expected-behavior.md) from the runner.

Prepare two disposable git repositories, each with a `.gitignore` for Python caches.

**`checkout`**: a copy of the supplied core checkout's tracked files, including manifests, catalogs and `example-workflows/shared`, so the baseline unit tests pass. Add one complete example library, `example-workflows/notes`, with its manifests:
- `skills/meeting-notes/SKILL.md` makes notes from a transcript, then independently reviews them. Its body repeats the note criteria already in the library's `guidance/writing.md`.
- `skills/meeting-actions/SKILL.md` extracts action items from finished notes, then independently reviews those same notes again.
- `skills/meeting-packet/SKILL.md` composes the two, so each packet's notes get two independent reviews.
- `skills/meeting-actions/scripts/count_actions.py`, with sibling `tests/`, crashes on notes that have no action items. The existing tests do not cover that case.
- `guidance/writing.md` includes one line marked as a correction for an older model: "IMPORTANT: you MUST ALWAYS name an owner for EVERY action item."
- One executable trial for `meeting-packet` (`case.json`, `request.md`, `expected-behavior.md`).

**`home`**: an Orchflows home with a user library `personal`:
- Its workflow `standup` drafts a standup in a terse style that its README calls deliberate.
- Its `guidance/standup.md` links to a missing reference.
- Leave one uncommitted edit in `standup`.

Supply research as fixtures, not live reads: dated release notes for the "new" model, stating that it follows repeated emphatic instructions too literally.

> [invoke `orchflows-review:orchflows-review`] A new model shipped. Review Orchflows and my libraries. Research only from the supplied sources. Save the run in the supplied output location.

Run from `checkout` as the workspace, with `home` as the Orchflows home and an output location outside both. Where no authenticated host CLI is available for E2E runs, the run reports that gap.

Tester only: in a separate session, also give a single agent the same request on fresh copies of both repositories, without this workflow. Report the planted findings each found, and the tokens each used.
