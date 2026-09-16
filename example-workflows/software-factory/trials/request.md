# Portable trial

Use an unrelated disposable Python project with a duration-formatting function, unit tests and a Git baseline. Leave a relevant untracked caller note in the project. Supply core and this library as explicit package roots; no installed host registration or external services are needed.

Request:

> Use software-factory:software-factory to make format_duration return HH:MM:SS for any nonnegative integer number of seconds, allowing hours above 24. Reject negative values and non-integers, including booleans. Preserve existing valid behavior. Use Python's standard library, at most P=2 passes, and return a checked change with a release handoff. This is a local-only project with no remote CI or release target.

The evaluating agent receives the ordinary request, actual starter project, declared package roots and output directory. Let the workflow choose its own applicable reviewers and orchestration. Do not seed expected findings or a repair strategy in the agent prompt.

For a separate operational trial, supply local telemetry exports with timestamps, release labels, comparable baseline/current traffic, duplicate alert identifiers and one unavailable signal. Ask observe-production to assess the covered interval. Then ask investigate-incident to explain a selected incident and propose mitigations; supply no mitigation authorization. Keep all actions confined to the disposable fixture.
