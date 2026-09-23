# Expected behavior

- Demonstrates bounded overlap with observed timestamps and serial/concurrent wall time, without attributing throughput to lower task latency.
- Terminates/reaps the owned child tree on the supported platform; interruption leaves durable identities and partial results. Unsupported platforms remain untested.
- Counts all launches and retry cost, retries only the declared transient fault and treats declared agent time exhaustion separately from setup or verifier failure.
- Resume does not duplicate completed trials, refuses changed benchmark/condition identity and records interrupted or uncertain remote work. One run directory has one active owner.
- Summary exposes planned/launched/completed/scored/unscored/canceled/not-launched counts and reasons. No stand-in score becomes a capability claim.
