# Request

Build a benchmark around the supplied slow command adapter. First validate its execution machinery using deterministic controls: overlap independent work at concurrency two, inject one transient setup failure, one timeout with a child process, and one grader crash. Cap this mechanics run at eight launches, one transient retry and two minutes. Interrupt and resume a separate short run to check durable partial results. Use no paid services. Record these as harness checks, not agent capability. Describe what real candidate execution is still needed.

Trial setup: provide a command fixture with documented slow/success/transient-failure modes, an owned child-process mode and an injected grader failure. Use disposable local files only. This stand-in is deliberately not a benchmarked agent.
