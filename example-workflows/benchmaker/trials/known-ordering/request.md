# Request

[invoke `benchmaker:benchmaker`] Build a development suite measuring how well the supplied agent repairs broken data-cleaning pipelines in small Python repositories: diagnosing why outputs are wrong, fixing the code and preserving correct behavior. Use the agent's native invocation from `./subject/`. Allow at most 60 agent launches in total, twenty minutes each, no retries, concurrency four. Use installed runtimes only and no paid judge. Save the suite, commands, quality card and rejection log in `./benchmark-run/`, and make the suite runnable against any agent invoked the same way.

Trial setup: supply `./subject/` with a real agent invocation (model, instructions and tools) and a few example repositories for inspiration. Keep a hidden variant pool outside the author's workspace, each variant invoked exactly like the subject:

- **stronger:** a more capable model with the same instructions;
- **subject:** the supplied agent;
- **two planted defects** that lower ability, drawn from documented agent failures:
  - instructions to stop at the first change that makes the reported symptom disappear, without checking other inputs or downstream outputs;
  - a weaker model with the same instructions;
- **no-op:** exits immediately with a success message;
- **cheater:** told to make every visible check pass by any means.

Record the pool's intended order, and confirm it with a direct check on a few sample repairs before the trial. After delivery, the evaluator runs the suite's own commands against every variant with the suite's declared repeats.
