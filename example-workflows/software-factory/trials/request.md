# Portable trials

Apply core `docs/hosts.md#workflow-trials`. Create an unrelated disposable synthetic Python project with duration formatting, unit tests, Git baseline and relevant untracked caller note. Supply core/library roots and output directory; no registration or external service is required. Give the runner only the ordinary request and fixtures, not expected findings or repair strategy.

> [invoke `software-factory:software-factory`] Make format_duration return HH:MM:SS for every nonnegative integer number of seconds, allowing hours above 24. Reject negatives and non-integers, including booleans; preserve valid behavior. Use Python's standard library, P=2 maximum and a checked release handoff. This local-only fixture has no remote CI or release target.

Separately, create synthetic telemetry with timestamps, releases, comparable baseline/current traffic, duplicate alert IDs and one unavailable signal. Use `[invoke software-factory:observe-production]` to assess its interval, then `[invoke software-factory:investigate-incident]` to explain one incident/propose mitigations without mitigation authority. Keep effects local; simulate integrations with captured payloads rather than live services.
