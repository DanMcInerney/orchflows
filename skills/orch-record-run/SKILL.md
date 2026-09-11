---
name: orch-record-run
description: Record a compact orchflows workflow run and its actual outcome in the user's configured home, reusing an existing run when workflows are composed.
---

Use one home run for the outer workflow. If the caller supplies a run directory and output context, reuse and pass them to composed skills and workers; the owner of that run alone finalizes it. Recording a run does not launch an agent.

Resolve the home from the caller's explicit choice, then `ORCHFLOWS_HOME`, then `~/.orchflows`. Use its `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python` elsewhere to invoke the absolute `.local/packages/orchflows-light/scripts/orchflows.py` path. If the home, runtime or installed CLI is absent, state the history gap and continue the requested work; use [orch-setup](../orch-setup/SKILL.md) when setting up the home is within the request. Do not assume the current directory is a package checkout.

For a new outer run, invoke that interpreter and script with:

```text
run start --workflow LIBRARY:SKILL --home HOME
```

Replace the uppercase arguments with the actual native package and skill identity and resolved home. Add `--project ALIAS` only for a known portable project alias; do not put a local project path in that field. Keep the returned `run_dir`, `run_json`, home and output context. The JSON records a unique UTC run ID, actual start time, workflow identity and readable home package/skill fingerprints when available. Those fingerprints describe home files; they cannot establish which cached native copy a host loaded. Include an observed loaded-version discrepancy in the summary when relevant.

Put receipts or existing native source logs in `run_dir/raw/` and bulk deliverables in `run_dir/artifacts/`, creating those subdirectories as needed. Honor explicitly requested output paths and include a reference to those outputs in the run summary. Carry this context through nested composition, including delegated orchestration. Do not copy credentials, raw prompts or whole host transcripts into history, invent activity counts or infer performance metrics. The helper records workflow summaries; it does not capture native host telemetry.

When work stops, write a concise UTF-8 summary of the actual request, result, checks or evidence, useful artifact/source-log references and unresolved gaps. Use project aliases and relative paths for portable references where possible. Keep sensitive task detail out unless the user requested it. Save the draft under `run_dir/artifacts/` or an existing output workspace, then invoke:

```text
run finish RUN_DIR --status complete --summary SUMMARY_FILE --home HOME
```

Choose `complete` for a fulfilled request, `partial` for useful unfinished work, or `blocked` when an external condition prevents progress. The helper copies the supplied bytes to `summary.md` and atomically finalizes `run.json`; it does not generate the summary. Report a logging error and preserve the deliverable if recording fails.

An already finalized run accepts only the identical status and exact summary bytes, preserving the original finish time. A changed outcome needs a new run. A concurrent finish returns a lock error; retry after that writer completes. If a stopped process left `.finish.lock`, inspect the run and confirm no writer is active before removing only that lock. After an interrupted metadata write, retry with the same summary. Preserve conflicting existing data and report the gap rather than silently rewriting history.

`run.json` and `summary.md` are compact, trackable history; raw files and bulk artifacts are ignored by the configured home. Recording does not commit, publish or synchronize the home.
