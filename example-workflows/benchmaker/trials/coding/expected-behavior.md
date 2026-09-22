# Expected behavior

- Invokes the real workflow on fresh task workspaces, preserving instructions, tools and declared settings.
- Uses outcome checks and regressions on delivered code; runner unit tests and prompt inspection remain harness evidence only.
- Accepts a valid alternative implementation, rejects a plausible incomplete patch and checks an unchanged-project control.
- Keeps evaluator checks/references out of solver inputs and accurately states the local access boundary.
- Retains patches, command output, scores, identities and cost/time limits. Changed cases after pilot are newly identified development revisions.
