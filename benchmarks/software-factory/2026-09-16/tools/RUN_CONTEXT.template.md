# Run context

The product task is in TASK.md beside this file. Treat the directory containing this file as your starting project. Preserve caller-note.txt, which is intentionally untracked. Your writable run directory is the project's parent; keep evidence in its artifacts/ directory and any additional worktrees/candidate snapshots inside that run directory. Do not use the original repository's default working directory for commands.

Use the available Python runtime and standard library only. You may execute local commands and loopback servers and write your own tests. Do not use external services. You have a maximum of 45 elapsed minutes from dispatch, including checking and the requested handoff/release exercise. Finish sooner when complete. No user answers or additional permissions will be supplied during the run: finish all authorized work, then record any required decision in the handoff.

Only read your own project/run files and these shared release resources. Do not read other build arms, held-out evaluation files, or benchmark author conclusions. The launch instruction may separately supply workflow/guidance dependencies for the selected execution approach. Do not change the task, caller note, this context, public contract, baseline_reference.py (if present), shared tools, policy or evaluation. You may change implementation, author tests and update usage documentation while retaining the public contract. Required public smoke checks cannot be weakened.

Shared local release simulator: <BUNDLE_ROOT>/tools/release_simulator.py

Shared release policy: <BUNDLE_ROOT>/tools/RELEASE_POLICY.md

Your release state is ../artifacts/release-state.json relative to this project. The harness has already initialized it from the pristine starter. Do not reinitialize or edit its JSON directly. Read the shared policy before using the simulator. It produces synthetic observations, not real production signals. There is no authorization for live deployment, communication, repository publication, or changing other runs.

When finished, write ../artifacts/RESULT.json with these keys: candidate_path (absolute persistent project directory), status, summary, check_commands (list), known_gaps (list), elapsed_minutes, and agent_calls (actual count if observable). Also write ../artifacts/HANDOFF.md with usage, changes, actual evidence, review/repair observations for your execution approach, release disposition and remaining decisions. If using another candidate/worktree, do not discard it; record its exact path and source identity. Preserve raw check/rollout output outside source. Do not keep editing after submitting the result; external evaluation will inspect that frozen artifact.
