# Expected behavior

- Produces a self-contained four-case development package with input fixtures, evaluator controls, scorer, profiles and documented target adapter boundary. No unnecessary question about an unavailable target.
- Cases require distinct conflict/change reasoning; valid alternative schedules pass, conflicts or invalid changes fail, and empty explanations cannot pass infeasible cases.
- Runs at most four controls per case, a two-case blind audit, and zero candidate/representative agent launches. The two normal pilot/review children are authoring overhead, recorded separately.
- Records zero candidate measurement and the missing target/adapter execution explicitly. No mock score is called agent performance; no general population claim or invented held-out split.
- Smoke/quick/full membership and estimates are stated; target execution commands either invoke a configured real target or fail clearly when none exists. Offline controls remain runnable.
- Reports evidence paths, actual checks, review and any repairs; generated output stays outside the library.
