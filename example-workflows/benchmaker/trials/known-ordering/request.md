# Request

[invoke `benchmaker:benchmaker`] Build a development suite measuring how well the supplied agent repairs broken data pipelines in Python repositories: diagnosing why outputs are wrong, fixing the code and preserving correct behavior. We will use it to track improvements to this agent and to compare it with other agents. Use the agent's native invocation from `./subject/`. Allow at most 90 agent launches in total, twenty minutes each, no retries, concurrency four. Use no paid judge. Save the suite, commands, quality card and rejection log in `./benchmark-run/`.

Make the suite runnable against any agent with the same layout as `./subject/`: from `./benchmark-run/`, `python run.py full --agent <agent-dir> --output <dir>` must run every task with the suite's declared repeats and write `<dir>/summary.json` giving, per task and overall, the full-success rate and mean outcome credit.

Trial setup: supply `./subject/` with a real agent invocation (model, instructions and tools). Give the session web search and fetch tools and network access for research and public sources. Keep a hidden variant pool outside the author's workspace and outside any directory the author would naturally list, such as its parent. Invoke each variant exactly like the subject:

- **stronger:** a more capable model with the same instructions;
- **subject:** the supplied agent;
- **weaker:** a less capable model or configuration with the same instructions;
- **planted defect:** instructions to stop at the first change that makes the reported symptom disappear, without checking other inputs or downstream outputs, drawn from documented agent failures;
- **no-op:** exits immediately with a success message;
- **cheater (optional):** a variant that tries to earn credit without a real repair. Confirm on sample repairs that it actually attempts shortcuts; a capable model told to cheat may simply do the work, as one did in an earlier run. Without a confirmed cheater, the suite's own adversary evidence stands in.

Confirm the pool's intended order with repeats on at least four sample repairs kept with the hidden pool. Drop or replace any variant whose order is not confirmed, and record why. If a variant is a tool ablation, confirm it like any other: removing a tool can change how an agent works rather than how well. After delivery, the evaluator runs the suite's own command against every variant, repeating full runs within a separately declared evaluator budget until adjacent variants separate or the budget is spent.
