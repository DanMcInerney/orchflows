# Hacker News selection and resume trial

Apply core `docs/hosts.md#workflow-trials` from an unrelated disposable workspace with the installed library or its supplied root and a Python 3.9+ interpreter. This request authorizes live, keyless, read-only Hacker News requests within the stated bounds; they are the trial's only external effect. Give the runner only the requests below and an output directory; keep the acceptance criteria separate. Replace the dates when testing another period. For a trial without network access, `scripts/acquire_fixture.py` covers parsing and resume offline instead.

> [invoke `research-acquire:research-acquire`] Collect Hacker News evidence about developers' experience adopting uv for Python projects, published from 2026-08-12 through 2026-09-11. Use one plan capped at 3 steps, 8 requests, 50 records and 120 seconds of active acquisition. Discover up to 10 stories, then select at most 2 discussions worth reading, up to 20 records each, explaining each choice and what you left unread. Save the plan, evidence, selection reasons, receipts and resume state in the supplied output directory, and report coverage gaps.

Then, in a fresh session with the same output directory:

> [invoke `research-acquire:research-acquire`] Resume the acquisition saved in the supplied output directory without changing its plan. Report whether any further requests were made and what evidence and gaps the directory now holds.

To exercise interrupted resume as well, stop the first session once during a depth read, record when, and then send the resume request. These bounds are trial inputs, not skill defaults.
