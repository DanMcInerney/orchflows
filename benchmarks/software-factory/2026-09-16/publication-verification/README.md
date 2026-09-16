# Checks of the published copies

These checks ran during publication on September 16, 2026. They are separate from the original experiment. No archived application, evaluator, patch or historical score was changed in response.

| Published candidate | Fresh result | Evidence |
| --- | --- | --- |
| Webhook / factory, first attempt | 27 pass, 0 fail, 1 evaluator startup error | [Result](webhook-inbox-workflow.json) |
| Webhook / factory, second attempt | 27 pass, 0 fail, 1 evaluator startup error | [Result](webhook-inbox-workflow-retry.json) |
| Webhook / single agent | 28/28 pass | [Result](webhook-inbox-single.json) |
| Logs / factory | 31/31 and speed target pass | [Result](log-archive-workflow.json) |
| Logs / single agent | 31/31 and speed target pass | [Result](log-archive-single.json) |

In the two workflow webhook attempts, `evaluation/webhook-inbox/harness.py:75` raised Windows `PermissionError` while reading its own `ready-1.json` file in `Sandbox.start()`. The first interrupted `concurrent_distinct_no_lost_rows`; the second interrupted `identical_retry_idempotent`. These errors happened before those checks' assertions. They expose a readiness-file access limitation in the archived evaluator; there is no claim of a successful fresh full workflow-webhook run. Other named checks passed in each run. Both failures are retained; retries stopped after the second attempt.

The applications, evaluator Python files and original external scores were hash-checked before and after these runs and remained unchanged. Performance was measured sequentially; new timings are publication checks and do not replace the original figures. Supporting paths in these fresh reports are normalized to the same placeholders as the archive.

Publication integrity checks separately verified all 434 original-to-published manifest entries, 77 byte-identical Python files, 10 byte-identical patches/diffs and 8 byte-identical prompts; the staged Git blobs also match the published hashes. The repository suite passed 60 tests with one skipped. Markdown link and high-confidence credential-pattern checks passed. See [the publication manifest](../PUBLICATION.json) for redaction and exclusion rules.
